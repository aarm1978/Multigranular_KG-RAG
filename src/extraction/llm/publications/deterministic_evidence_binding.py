"""Bind model-authored literal Publication evidence before canonical validation."""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

from src.extraction.llm.publications.request_builder import sha256_bytes


EVIDENCE_BINDING_VERSION = "publication-deterministic-evidence-binding-0.1.0"
COMPUTED_EVIDENCE_FIELDS = frozenset({
    "startOffsetInUnit", "endOffsetInUnit", "startOffsetInDocument",
    "endOffsetInDocument", "evidenceHash",
})
LOCATOR_ANCHOR_FIELD = "locatorAnchor"


def _occurrences(text: str, literal: str) -> list[int]:
    """Return all exact Unicode code-point occurrences, including overlaps."""

    starts: list[int] = []
    cursor = 0
    while True:
        start = text.find(literal, cursor)
        if start < 0:
            return starts
        starts.append(start)
        cursor = start + 1


def bind_evidence_spans(
    payload: Mapping[str, Any], source_unit: Mapping[str, Any]
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Return canonical-ready evidence spans or explicit fail-closed findings.

    The model remains the authority for ``evidenceText``. This function never changes
    that text, normalizes strings, or chooses an ambiguous occurrence.
    """

    bound = deepcopy(dict(payload))
    source_text = source_unit.get("text")
    document_start = source_unit.get("startOffsetInDocument")
    findings: list[dict[str, Any]] = []
    spans = bound.get("evidenceSpans", [])
    if not isinstance(source_text, str) or not isinstance(document_start, int):
        raise ValueError("trusted source unit lacks text or document start")
    if not isinstance(spans, list):
        return bound, {"bindingStatus": "failed", "findings": [{"code": "EVIDENCE_BINDING_SPANS_NOT_ARRAY", "pointer": "/evidenceSpans"}]}

    for index, span in enumerate(spans):
        pointer = f"/evidenceSpans/{index}"
        if not isinstance(span, dict):
            findings.append({"code": "EVIDENCE_BINDING_SPAN_NOT_OBJECT", "pointer": pointer})
            continue
        literal = span.get("evidenceText")
        if not isinstance(literal, str) or not literal:
            findings.append({"code": "EVIDENCE_BINDING_LITERAL_INVALID", "pointer": pointer + "/evidenceText"})
            continue
        matches = _occurrences(source_text, literal)
        start: int | None = None
        anchor = span.pop(LOCATOR_ANCHOR_FIELD, None)
        if len(matches) == 1:
            if anchor is not None and (not isinstance(anchor, str) or len(_occurrences(source_text, anchor)) != 1 or literal not in anchor):
                findings.append({"code": "EVIDENCE_BINDING_INVALID_LOCATOR_ANCHOR", "pointer": pointer + "/locatorAnchor"})
                continue
            start = matches[0]
        elif not matches:
            findings.append({"code": "EVIDENCE_BINDING_LITERAL_NOT_FOUND", "pointer": pointer + "/evidenceText"})
            continue
        else:
            if not isinstance(anchor, str) or not anchor:
                findings.append({"code": "EVIDENCE_BINDING_AMBIGUOUS_LITERAL_REQUIRES_LOCATOR_ANCHOR", "pointer": pointer + "/locatorAnchor"})
                continue
            anchor_matches = _occurrences(source_text, anchor)
            if len(anchor_matches) != 1 or literal not in anchor:
                findings.append({"code": "EVIDENCE_BINDING_INVALID_LOCATOR_ANCHOR", "pointer": pointer + "/locatorAnchor"})
                continue
            anchor_start = anchor_matches[0]
            local_matches = _occurrences(anchor, literal)
            if len(local_matches) != 1:
                findings.append({"code": "EVIDENCE_BINDING_AMBIGUOUS_LITERAL_WITHIN_LOCATOR_ANCHOR", "pointer": pointer + "/locatorAnchor"})
                continue
            start = anchor_start + local_matches[0]
        assert start is not None
        end = start + len(literal)
        span.update({
            "startOffsetInUnit": start,
            "endOffsetInUnit": end,
            "startOffsetInDocument": document_start + start,
            "endOffsetInDocument": document_start + end,
            "evidenceHash": sha256_bytes(literal.encode("utf-8")),
        })
    return bound, {
        "bindingVersion": EVIDENCE_BINDING_VERSION,
        "bindingStatus": "bound" if not findings else "failed",
        "findings": findings,
    }
