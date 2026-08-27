"""Strict provider-neutral Publication response parsing for M1 development runs."""

from __future__ import annotations

import json
from typing import Any, Mapping

from src.extraction.llm.publications.request_builder import (
    canonical_json,
    expected_candidate_metadata,
    sha256_bytes,
)


PARSER_VERSION = "0.1.0"
SEMANTIC_RESPONSE_KEYS = {
    "candidateNodes",
    "candidateEdges",
    "evidenceSpans",
    "abstentions",
    "deferredRecords",
}


def parse_recorded_response(
    raw_response: bytes, request: Mapping[str, Any]
) -> dict[str, Any]:
    """Strictly parse one raw response and bind permitted pipeline-owned metadata.

    Malformed JSON is returned as a processing failure. No regex salvage, repair, or
    semantic correction is performed. JSON values that are structurally wrong remain in
    the parsed envelope for the V2 schema validator to reject.
    """

    raw_hash = sha256_bytes(raw_response)
    try:
        decoded = raw_response.decode("utf-8")
        payload = json.loads(decoded)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        return {
            "parserVersion": PARSER_VERSION,
            "parseStatus": "processing_failed",
            "processingCode": "INVALID_JSON",
            "rawResponseSha256": raw_hash,
            "error": str(exc),
        }
    if not isinstance(payload, dict):
        return {
            "parserVersion": PARSER_VERSION,
            "parseStatus": "parsed",
            "rawResponseSha256": raw_hash,
            "parsedDocument": payload,
            "parsedEnvelope": None,
            "bindingOperations": [],
        }

    envelope = {
        "schemaVersion": "0.1.0",
        "outputStage": "parsed_candidate",
        "metadata": expected_candidate_metadata(request, raw_hash),
        **payload,
    }
    unexpected = sorted(set(payload) - SEMANTIC_RESPONSE_KEYS)
    return {
        "parserVersion": PARSER_VERSION,
        "parseStatus": "parsed",
        "rawResponseSha256": raw_hash,
        "parsedDocument": payload,
        "parsedEnvelope": envelope,
        "bindingOperations": [
            {
                "operation": "bind_pipeline_metadata",
                "jsonPointer": "/metadata",
                "metadataSha256": sha256_bytes(canonical_json(envelope["metadata"])),
            }
        ],
        "unexpectedSemanticKeys": unexpected,
    }


def canonical_parsed_envelope(parser_result: Mapping[str, Any]) -> bytes:
    """Serialize a successfully parsed envelope deterministically."""

    if parser_result.get("parseStatus") != "parsed" or not isinstance(
        parser_result.get("parsedEnvelope"), dict
    ):
        raise ValueError("no canonical parsed envelope exists")
    return canonical_json(parser_result["parsedEnvelope"]) + b"\n"
