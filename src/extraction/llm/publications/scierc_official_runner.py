"""Prospective sequential SciERC traversal; no activation is supplied by this module."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import tarfile
import time
from urllib.error import URLError

from . import scierc_external_anchor as a
from . import scierc_smoke_runtime as s
from .openai_provider import extract_model_output, load_openai_api_key, validate_provider_response

CANDIDATE = a.PROJECT_ROOT / "data/curation/papers/m2/scierc_step9_preflight/scierc_preflight_candidate_v0.2.0.json"
CANDIDATE_SHA = "d5ed3987bc19c802087b8f214f8d96f371746c3b6a45c75e14768bb357bf04a1"
ROOT = a.RUNTIME_ROOT / "official_sequential_v0.1.0"
APPROVALS = a.RUNTIME_ROOT / "approvals/official_sequential_v0.1.0"
TIMEOUT = 600
SCOPE = "scierc-official-sequential/0.1.0"


class LocalTransportFailure(ValueError):
    """Expected single-attempt transport uncertainty, not a shared code defect."""


def require(value, code: str) -> None:
    """Stop on integrity or authorization failures."""
    if not value:
        raise ValueError(code)


def read(path: Path):
    """Read strict JSON without modifying evidence."""
    return s._strict_json(path.read_bytes())


def prepare() -> tuple:
    """Reconstruct exact bodies in candidate order using source only, never gold."""
    require(a.sha256_bytes(CANDIDATE.read_bytes()) == CANDIDATE_SHA, "CANDIDATE_HASH")
    candidate = read(CANDIDATE)
    source = a.source_freeze()
    require(a.sha256_bytes(a.SOURCE_FREEZE_PATH.read_bytes()) == candidate["source"]["sourceFreezeFileSha256"]
            and a.sha256_bytes(a.ADAPTER_FREEZE_PATH.read_bytes()) == candidate["source"]["adapterFreezeFileSha256"], "SOURCE_AUTHORITY_IDENTITY")
    require(source["officialArchive"]["sha256"] == candidate["source"]["archiveSha256"]
            and source["splits"]["test"] == candidate["source"]["test"], "FROZEN_SOURCE_BINDING")
    with a.ARCHIVE_PATH.open("rb") as handle:
        require(a._sha256_stream(handle) == source["officialArchive"]["sha256"], "ARCHIVE_HASH")
    spec = source["splits"]["test"]
    with tarfile.open(a.ARCHIVE_PATH, "r:gz") as archive:
        payload = archive.extractfile(spec["path"]).read()
    require(a.sha256_bytes(payload) == spec["sha256"], "SPLIT_HASH")
    documents = a.parse_processed_split(payload, include_gold=False)
    by_id = {doc.document_id: doc for doc in documents}
    ids = [row["documentID"] for row in candidate["requests"]]
    require(len(documents) == len(by_id) == len(ids) == len(set(ids)) == 100 and set(ids) == set(by_id), "MEMBERSHIP")
    prepared = []
    for row in candidate["requests"]:
        doc = by_id[row["documentID"]]
        body = a.canonical_json(a.build_request_body(doc))
        require(a.sha256_bytes(body) == row["providerRequestBodySha256"], "BODY_IDENTITY")
        prepared.append((doc, body))
    return candidate, prepared


def binding(candidate: dict, root: Path) -> dict:
    """Describe the new runner scope without granting approval."""
    return {"scope": SCOPE, "candidateSha256": CANDIDATE_SHA,
            "manifestSha256": candidate["manifestSha256"],
            "orderedRequestsSha256": a.sha256_bytes(a.canonical_json(candidate["requests"])),
            "runnerSha256": a.sha256_bytes(Path(__file__).read_bytes()),
            "dependencyRuntimeSha256": s.runtime_identity(), "runtimeRoot": str(root.resolve()),
            "maxGenerationPosts": 100, "concurrency": 1, "socketTimeoutSeconds": TIMEOUT,
            "automaticRedispatch": False}


def check_approvals(candidate: dict, root: Path, acceptance, authorization) -> None:
    """Require distinct linked records bound to every official request and runner."""
    expected = binding(candidate, root)
    for record, kind in ((acceptance, "runtime_acceptance"), (authorization, "live_authorization")):
        require(isinstance(record, dict) and record.get("kind") == kind and record.get("approved") is True, "MISSING_APPROVAL")
        require(record.get("binding") == expected and isinstance(record.get("recordID"), str) and record["recordID"].strip(), "APPROVAL_BINDING")
    require(authorization.get("acceptanceRecordID") == acceptance["recordID"] != authorization["recordID"], "APPROVAL_LINK")


def document_root(root: Path, document_id: str) -> Path:
    """Use stable safe paths, never document IDs as filesystem names."""
    return root / a.sha256_bytes(document_id.encode())


def run_document(doc, body: bytes, path: Path, api_key: str, transport) -> dict:
    """Preserve one attempt, classifying isolated output failures without repair."""
    path.mkdir()  # Existing state is never reused or overwritten.
    s._sync_directory(path.parent)
    s._write_new(path / "provider_request.json", body)
    started, tick = s._utc(), time.monotonic_ns()
    result = {"documentID": doc.document_id, "bodySha256": a.sha256_bytes(body),
              "requestedModel": "gpt-5.6-sol", "startedAt": started,
              "delivery": "unknown", "globalStop": False, "usage": None,
              "providerRequestID": None, "responseID": None, "socketTimeoutSeconds": TIMEOUT}
    s._json_new(path / "dispatch_started.json", {**result, "monotonicStartedNs": tick, "maxGenerationPosts": 1})

    def preserve(name: str, raw: bytes) -> bytes:
        """Preserve bytes exclusively; explicitly redact credential echoes only."""
        if api_key.encode() in raw:
            raw = raw.replace(api_key.encode(), b"[CREDENTIAL_REDACTED]")
            result["credentialEchoRedacted"] = True
        s._write_new(path / name, raw)
        return raw

    stage = "transport"
    try:
        try:
            reply = transport(api_key, body, TIMEOUT)
        except s.PartialTransportFailure as exc:
            preserve("partial_provider_response.bin", exc.partial)
            result.update(httpStatus=exc.http_status, providerRequestID=exc.request_id.replace(api_key, "[CREDENTIAL_REDACTED]") if exc.request_id else None)
            result["globalStop"] = exc.http_status in (400, 401, 403, 404, 422, 429)
            raise LocalTransportFailure("PARTIAL_RESPONSE") from None
        except (TimeoutError, ConnectionError, URLError) as exc:
            raise LocalTransportFailure(type(exc).__name__) from None
        result.update(httpStatus=reply.http_status, delivery="http_response_received",
                      providerRequestID=reply.request_id.replace(api_key, "[CREDENTIAL_REDACTED]") if reply.request_id else None)
        raw = preserve("provider_response.bin", reply.body)
        s._json_new(path / "provider_transport.json", {"providerRequestID": result["providerRequestID"],
            "httpStatus": reply.http_status, "receivedAt": s._utc()})
        # These statuses demonstrate shared request/auth/quota blockers even with a non-JSON body.
        result["globalStop"] = reply.http_status in (400, 401, 403, 404, 422, 429)
        stage = "provider_json"
        response = s._strict_json(raw)
        require(isinstance(response, dict), "PROVIDER_NOT_OBJECT")
        s._json_new(path / "provider_response.json", response)
        result.update(responseID=response.get("id"), returnedModel=response.get("model"), usage=response.get("usage"),
                      providerCreatedAt=response.get("created_at"), providerCompletedAt=response.get("completed_at"))
        error = response.get("error")
        code = error.get("code") if isinstance(error, dict) else None
        if code in {"insufficient_quota", "invalid_api_key", "billing_hard_limit_reached", "model_not_found", "invalid_json_schema"}:
            result["globalStop"] = True
        result["providerErrorCode"] = code
        outputs = response.get("output")
        fragments = [c["text"].encode() for item in (outputs if isinstance(outputs, list) else [])
                     if isinstance(item, dict) and isinstance(item.get("content"), list)
                     for c in item["content"] if isinstance(c, dict) and c.get("type") == "output_text" and isinstance(c.get("text"), str)]
        for index, fragment in enumerate(fragments):
            preserve(f"model_output_part_{index:03d}.bin", fragment)
        if len(fragments) == 1:
            preserve("raw_model_output.bin", fragments[0])
        stage = "http"
        require(200 <= reply.http_status < 300, "HTTP_FAILURE")
        stage = "provider_contract"
        if response.get("model") != "gpt-5.6-sol":
            result["globalStop"] = True
        validate_provider_response(response)
        stage = "model_output"
        require(isinstance(outputs, list), "OUTPUT_NOT_LIST")
        require(not any(c.get("type") == "refusal" for item in outputs if isinstance(item, dict)
                        and isinstance(item.get("content"), list) for c in item["content"] if isinstance(c, dict)), "REFUSAL")
        output = extract_model_output(response)
        stage = "model_json"
        prediction = s._strict_json(output)
        stage = "prediction_validation"
        a.validate_prediction(prediction, doc)
        s._json_new(path / "validated_prediction.json", prediction)
        result["terminalStatus"] = "completed_valid"
    except ValueError as exc:
        # Expected parser/validator defects are document-local; unexpected code errors propagate globally.
        if stage == "transport" and not isinstance(exc, LocalTransportFailure):
            result["globalStop"] = True
        result.update(terminalStatus="failed", failureStage=stage, failureCode=str(exc).replace(api_key, "[CREDENTIAL_REDACTED]"))
    result.update(completedAt=s._utc(), elapsedMilliseconds=(time.monotonic_ns() - tick) / 1_000_000)
    s._json_new(path / "terminal.json", result)
    return result


def summary(candidate: dict, root: Path, stop=None) -> dict:
    """Cover all IDs including interrupted states; never infer success from traversal."""
    rows = []
    for request in candidate["requests"]:
        doc_id = request["documentID"]; path = document_root(root, doc_id)
        row = {"documentID": doc_id, "artifactPath": str(path.relative_to(root)), "classification": "not_started"}
        if (path / "terminal.json").exists():
            try:
                terminal = read(path / "terminal.json")
                require(terminal["documentID"] == doc_id and terminal["bodySha256"] == request["providerRequestBodySha256"], "TERMINAL_IDENTITY")
                row.update(terminal)
                row["classification"] = "successful" if terminal["terminalStatus"] == "completed_valid" else "failed_uncertain"
            except (ValueError, KeyError, TypeError, OSError):
                stop = "GLOBAL_TERMINAL_INTEGRITY_FAILURE"
                row.update(classification="failed_uncertain", failureStage="integrity", failureCode="UNREADABLE_OR_MISMATCHED_TERMINAL", delivery="unknown")
        elif (path / "dispatch_started.json").exists():
            row.update(classification="failed_uncertain", terminalStatus="interrupted_nonterminal", delivery="unknown",
                       failureStage="interrupted", failureCode="NO_REDISPATCH")
            row.update(available_metadata(path))
        rows.append(row)
    counts = {key: sum(row["classification"] == key for row in rows) for key in ("successful", "failed_uncertain", "not_started")}
    return {"scope": SCOPE, "counts": counts, "documents": rows, "globalStop": stop,
            "completedTraversal": counts["not_started"] == 0 and all(row.get("terminalStatus") in {"completed_valid", "failed"} for row in rows),
            "allOutputsValid": counts["successful"] == 100, "automaticRedispatch": False}


def available_metadata(path: Path) -> dict:
    """Recover available IDs/usage/timing after interruption without inventing fields."""
    result = {}
    for name, fields in (("dispatch_started.json", {"startedAt": "startedAt", "requestedModel": "requestedModel"}),
                         ("provider_transport.json", {"providerRequestID": "providerRequestID", "httpStatus": "httpStatus"}),
                         ("provider_response.json", {"id": "responseID", "model": "returnedModel", "usage": "usage",
                                                     "created_at": "providerCreatedAt", "completed_at": "providerCompletedAt"})):
        try:
            value = read(path / name)
            result.update({target: value[source] for source, target in fields.items() if source in value})
        except (OSError, ValueError, TypeError):
            continue  # A partial write cannot be interpreted as a valid metadata object.
    return result


def append_failure(root: Path, result: dict, path: Path) -> None:
    """Durably append failures without rewriting previous records."""
    entry = {**result, "artifactPath": str(path.relative_to(root))}
    with (root / "failures.jsonl").open("ab") as handle:
        handle.write(a.canonical_json(entry) + b"\n"); handle.flush(); os.fsync(handle.fileno())
    s._sync_directory(root)


def execute(*, acceptance=None, authorization=None, api_key="", root: Path = ROOT, transport=None) -> dict:
    """Traverse once in candidate order; any existing run is report-only, never resumed."""
    candidate, documents = prepare()
    check_approvals(candidate, root, acceptance, authorization)
    require(bool(api_key), "CREDENTIAL_UNAVAILABLE")
    require(transport is not None or root.resolve() == ROOT.resolve(), "LIVE_NAMESPACE")
    identity = {"binding": binding(candidate, root), "acceptance": acceptance, "authorization": authorization}
    if os.path.lexists(root):
        require((root / "identity.json").exists() and read(root / "identity.json") == identity, "EXISTING_STATE_CONFLICT")
        return summary(candidate, root, "EXISTING_STATE_NO_REDISPATCH")
    root.parent.mkdir(parents=True, exist_ok=True)
    root.mkdir(); s._sync_directory(root.parent)  # Exclusive run claim, including concurrent launch protection.
    stop = None
    current = None
    loop_tick = None
    try:
        s._json_new(root / "identity.json", identity)
        for index, (doc, body) in enumerate(documents, 1):
            current = (index, doc, document_root(root, doc.document_id))
            state = summary(candidate, root)
            require(state["globalStop"] is None, "GLOBAL_EVIDENCE_INTEGRITY")
            counts = state["counts"]
            loop_tick = time.monotonic()
            print(f"[{index}/100] {doc.document_id} starting elapsed=0s successful={counts['successful']} failed={counts['failed_uncertain']}", flush=True)
            result = run_document(doc, body, current[2], api_key, s.exact_post if transport is None else transport)
            if result["terminalStatus"] != "completed_valid":
                append_failure(root, result, current[2])
            counts = summary(candidate, root)["counts"]
            print(f"[{index}/100] {doc.document_id} {result['terminalStatus']} elapsed={result['elapsedMilliseconds']/1000:.3f}s successful={counts['successful']} failed={counts['failed_uncertain']}", flush=True)
            if result["globalStop"]:
                stop = "SHARED_PROVIDER_BLOCKER"; break
    except (Exception, KeyboardInterrupt) as exc:
        stop = "PERSISTENCE_INTEGRITY_OR_CODE_STOP:" + type(exc).__name__
        if current:
            index, doc, path = current
            # Best effort only if persistence itself is failing. Never dispatch again.
            try:
                append_failure(root, {**available_metadata(path), "documentID": doc.document_id, "terminalStatus": "global_stop",
                    "failureStage": "orchestration", "failureCode": type(exc).__name__,
                    "delivery": "unknown" if (path / "dispatch_started.json").exists() else "not_dispatched"}, path)
            except (OSError, ValueError, TypeError):
                pass
            counts = summary(candidate, root)["counts"]
            elapsed = time.monotonic() - loop_tick if loop_tick is not None else 0
            print(f"[{index}/100] {doc.document_id} global_stop elapsed={elapsed:.3f}s successful={counts['successful']} failed={counts['failed_uncertain']}", flush=True)
    result = summary(candidate, root, stop)
    result["summaryPersisted"] = True
    try:
        s._json_new(root / "summary.json", result)
    except OSError:
        result.update(summaryPersisted=False, globalStop="SUMMARY_PERSISTENCE_FAILURE")
        print("GLOBAL PERSISTENCE STOP: summary cannot be saved; stdout summary remains available.", flush=True)
    return result


def main(argv=None) -> None:
    """Explicit manual-only entry point; no real approval records are generated."""
    parser = argparse.ArgumentParser(description="Prospective official SciERC runner; requires separate exact approvals.")
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args(argv)
    if not args.execute:
        print("NOT EXECUTED. Implementation only; official acceptance and authorization required.")
        return
    try:
        result = execute(acceptance=read(APPROVALS / "runtime_acceptance.json"),
                         authorization=read(APPROVALS / "live_authorization.json"), api_key=load_openai_api_key())
        print(json.dumps(result, sort_keys=True), flush=True)
    except (Exception, KeyboardInterrupt):
        print("STOPPED: preserve state; no retry or redispatch. Check approvals/integrity locally.", flush=True)
        raise SystemExit(1) from None


if __name__ == "__main__":
    main()
