"""Build deterministic positional evidence guidance for Publication M2-B3.

The guide is an auxiliary coordinate aid derived only from the exact source-unit text.
It neither identifies semantic evidence nor changes any frozen candidate or validation
contract. Historical M2-A/B1/B2 provider-input builders intentionally remain untouched.
"""

from __future__ import annotations

from copy import deepcopy
import re
from typing import Any, Mapping

from src.extraction.llm.publications.openai_provider import build_provider_input
from src.extraction.llm.publications.request_builder import canonical_json, sha256_bytes


COORDINATE_GUIDE_VERSION = "publication-evidence-coordinate-guide-0.1.0"
COORDINATE_GUIDE_PATTERN = r"\w+|[^\w\s]"
COORDINATE_GUIDE_REGEX = re.compile(COORDINATE_GUIDE_PATTERN, re.UNICODE)
COORDINATE_GUIDE_SEPARATOR = (
    "\n\nDeterministic trusted evidence-coordinate guide JSON:\n"
)


def build_evidence_coordinate_guide(source_unit: Mapping[str, Any]) -> dict[str, Any]:
    """Derive ordered token-boundary records from regex match spans."""

    text = source_unit["text"]
    document_start = source_unit["startOffsetInDocument"]
    if not isinstance(text, str) or not isinstance(document_start, int):
        raise ValueError("source unit must provide text and an integer document start")
    entries = []
    for ordinal, match in enumerate(COORDINATE_GUIDE_REGEX.finditer(text), start=1):
        unit_start, unit_end = match.span()
        entries.append(
            {
                "tokenOrdinal": ordinal,
                "tokenText": match.group(0),
                "startOffsetInUnit": unit_start,
                "endOffsetInUnit": unit_end,
                "startOffsetInDocument": document_start + unit_start,
                "endOffsetInDocument": document_start + unit_end,
            }
        )
    return {
        "coordinateGuideVersion": COORDINATE_GUIDE_VERSION,
        "purpose": "deterministic_positional_coordinate_aid_only",
        "semanticEvidenceAuthority": False,
        "offsetSemantics": "zero_based_half_open_unicode_code_points",
        "tokenOrdinalBase": 1,
        "tokenization": {
            "pattern": COORDINATE_GUIDE_PATTERN,
            "unicode": True,
            "positionSource": "regex_match_span",
        },
        "sourceUnitID": source_unit["sourceUnitID"],
        "sourceUnitTextHash": source_unit["textHash"],
        "sourceUnitStartOffsetInDocument": document_start,
        "entries": entries,
    }


def audit_evidence_coordinate_guide(
    source_unit: Mapping[str, Any], guide: Mapping[str, Any]
) -> dict[str, Any]:
    """Fail closed unless every guide coordinate is an exact deterministic boundary."""

    text = source_unit["text"]
    document_start = source_unit["startOffsetInDocument"]
    entries = list(guide.get("entries", []))
    findings: list[dict[str, Any]] = []
    coverage = [0] * len(text)
    previous_end = 0
    for index, entry in enumerate(entries, start=1):
        path = f"/entries/{index - 1}"
        start = entry.get("startOffsetInUnit")
        end = entry.get("endOffsetInUnit")
        if entry.get("tokenOrdinal") != index:
            findings.append({"path": path + "/tokenOrdinal", "code": "INVALID_ORDINAL"})
        if not isinstance(start, int) or not isinstance(end, int) or not (0 <= start < end <= len(text)):
            findings.append({"path": path, "code": "INVALID_UNIT_SPAN"})
            continue
        if start < previous_end:
            findings.append({"path": path, "code": "OVERLAPPING_OR_UNORDERED"})
        previous_end = end
        if text[start:end] != entry.get("tokenText"):
            findings.append({"path": path + "/tokenText", "code": "TOKEN_TEXT_MISMATCH"})
        if entry.get("startOffsetInDocument") != document_start + start:
            findings.append({"path": path + "/startOffsetInDocument", "code": "DOCUMENT_START_MISMATCH"})
        if entry.get("endOffsetInDocument") != document_start + end:
            findings.append({"path": path + "/endOffsetInDocument", "code": "DOCUMENT_END_MISMATCH"})
        for offset in range(start, end):
            coverage[offset] += 1
    for offset, character in enumerate(text):
        expected = 0 if character.isspace() else 1
        if coverage[offset] != expected:
            findings.append(
                {
                    "path": f"/sourceUnit/text/{offset}",
                    "code": "NONWHITESPACE_COVERAGE_MISMATCH",
                    "expected": expected,
                    "observed": coverage[offset],
                }
            )
    canonical = canonical_json(guide)
    return {
        "auditSchemaVersion": "0.1.0",
        "valid": not findings,
        "findings": findings,
        "entryCount": len(entries),
        "canonicalBytes": len(canonical),
        "coordinateGuideSha256": sha256_bytes(canonical),
    }


def coordinate_guide_record(
    source_unit: Mapping[str, Any], guide: Mapping[str, Any]
) -> dict[str, Any]:
    """Describe guide derivation and deterministic reproducibility."""

    audit = audit_evidence_coordinate_guide(source_unit, guide)
    if not audit["valid"]:
        raise ValueError("coordinate guide failed deterministic audit")
    return {
        "recordSchemaVersion": "0.1.0",
        "artifactRole": "trusted_auxiliary_evidence_coordinate_guide",
        "developmentOnly": True,
        "coordinateGuideVersion": COORDINATE_GUIDE_VERSION,
        "constructionDeterministic": True,
        "semanticEvidenceAuthority": False,
        "tokenizationPattern": COORDINATE_GUIDE_PATTERN,
        "positionsTakenFromRegexMatchSpans": True,
        "textSearchUsedForPositioning": False,
        "sourceUnitID": source_unit["sourceUnitID"],
        "sourceUnitTextHash": source_unit["textHash"],
        **audit,
    }


def build_coordinate_guided_provider_input(
    request: Mapping[str, Any], guide: Mapping[str, Any]
) -> bytes:
    """Append the explicit guide section to the unchanged bounded provider input."""

    return (
        build_provider_input(request)
        + COORDINATE_GUIDE_SEPARATOR.encode("utf-8")
        + canonical_json(deepcopy(dict(guide)))
    )
