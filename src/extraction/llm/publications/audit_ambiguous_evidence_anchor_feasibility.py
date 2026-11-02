"""Measure exact-text locator anchors for the three preserved ambiguous evidence spans."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any, Mapping, Sequence

from src.extraction.llm.publications.audit_authentic_evidence_binding_feasibility import (
    DEFAULT_OUTPUT_DIR,
    _occurrences,
    _paths,
)
from src.extraction.llm.publications.request_builder import (
    canonical_json,
    canonical_json_file,
    load_json_object,
    sha256_bytes,
)


AUDIT_VERSION = "publication-ambiguous-evidence-anchor-feasibility/0.1.0"
AMBIGUOUS_AUDIT_PATH = (
    DEFAULT_OUTPUT_DIR / "publication_authentic_evidence_binding_feasibility_audit.json"
)


def _minimum_unique_anchor(text: str, start: int, literal: str) -> dict[str, Any] | None:
    """Find the shortest exact contiguous unique anchor around one witnessed occurrence."""

    end = start + len(literal)
    for added in range(1, len(text) - len(literal) + 1):
        for left in range(added + 1):
            right = added - left
            if start - left < 0 or end + right > len(text):
                continue
            anchor = text[start - left:end + right]
            if len(_occurrences(text, anchor)) == 1:
                if anchor.find(literal) != left:
                    raise ValueError("anchor does not retain the original literal exactly")
                return {
                    "anchorText": anchor,
                    "anchorCodePointLength": len(anchor),
                    "anchorUtf8Bytes": len(anchor.encode("utf-8")),
                    "addedLeftCodePoints": left,
                    "addedRightCodePoints": right,
                    "addedLeftUtf8Bytes": len(text[start - left:start].encode("utf-8")),
                    "addedRightUtf8Bytes": len(text[end:end + right].encode("utf-8")),
                    "exactOccurrenceCount": 1,
                    "originalLiteralStartInAnchor": left,
                }
    return None


def _line_envelope(text: str, start: int, end: int) -> dict[str, Any]:
    """Return the exact line envelope as a syntactic, not semantic, extension probe."""

    line_start = text.rfind("\n", 0, start) + 1
    line_end_index = text.find("\n", end)
    line_end = len(text) if line_end_index < 0 else line_end_index
    envelope = text[line_start:line_end]
    return {
        "structuralEnvelope": "line",
        "text": envelope,
        "codePointLength": len(envelope),
        "utf8Bytes": len(envelope.encode("utf-8")),
        "exactOccurrenceCount": len(_occurrences(text, envelope)) if envelope else 0,
        "originalLiteralStartInEnvelope": start - line_start,
        "isUnique": bool(envelope) and len(_occurrences(text, envelope)) == 1,
    }


def audit_case(development_id: str, evidence_span_id: str) -> dict[str, Any]:
    """Audit one ambiguous authentic span while retaining its current evidence text."""

    paths = _paths(development_id)
    payload = load_json_object(paths["raw"])
    request = load_json_object(paths["request"])
    span = next(item for item in payload["evidenceSpans"] if item["evidenceSpanID"] == evidence_span_id)
    text = request["sourceUnit"]["text"]
    literal = span["evidenceText"]
    starts = _occurrences(text, literal)
    returned_start = span["startOffsetInUnit"]
    if returned_start not in starts:
        raise ValueError(f"{development_id} {evidence_span_id} returned offset is not an exact occurrence")
    anchor = _minimum_unique_anchor(text, returned_start, literal)
    if anchor is None:
        return {
            "developmentID": development_id,
            "evidenceSpanID": evidence_span_id,
            "originalEvidenceText": literal,
            "classification": "unresolved_fail_closed",
            "exactOccurrenceCount": len(starts),
        }
    line = _line_envelope(text, returned_start, returned_start + len(literal))
    return {
        "developmentID": development_id,
        "evidenceSpanID": evidence_span_id,
        "sourceUnitID": request["sourceUnit"]["sourceUnitID"],
        "originalEvidenceText": literal,
        "originalEvidenceTextSha256": sha256_bytes(literal.encode("utf-8")),
        "originalCodePointLength": len(literal),
        "originalUtf8Bytes": len(literal.encode("utf-8")),
        "exactOccurrenceCount": len(starts),
        "allOccurrenceStartOffsetsInUnit": starts,
        "historicalReturnedStartOffsetInUnit": returned_start,
        "historicalOffsetSelectsExactOccurrence": True,
        "minimumUniqueLocatorAnchor": {
            **anchor,
            "anchorTextSha256": sha256_bytes(anchor["anchorText"].encode("utf-8")),
        },
        "locatorAnchorVerification": {
            "anchorOccursExactlyOnce": True,
            "originalEvidenceOccursAtRecordedAnchorPosition": True,
            "deterministicCoordinatesRecoverableFromUniqueAnchor": True,
            "usesNormalization": False,
            "usesFuzzyMatching": False,
            "usesCoordinateGuide": False,
            "usesModelGeneratedOffsets": False,
        },
        "semanticEvidenceExtension": {
            "determination": "not_established_fail_closed",
            "reason": "semantic coherence and assertion-support preservation require researcher/contract authority",
            "structuralExactLineProbe": {
                key: value for key, value in line.items() if key != "text"
            },
            "lineTextSha256": sha256_bytes(line["text"].encode("utf-8")),
            "canBecomeUniqueAsStructuralExactLine": line["isUnique"],
            "isNotASemanticExtensionDecision": True,
        },
    }


def build_audit() -> dict[str, Any]:
    """Run the complete three-case audit from the committed ambiguity inventory."""

    prior = load_json_object(AMBIGUOUS_AUDIT_PATH)
    cases = [
        (unit["developmentID"], span["evidenceSpanID"])
        for unit in prior["units"]
        for span in unit["evidenceSpanRows"]
        if span["classification"] == "multiple_exact_occurrences"
    ]
    rows = [audit_case(*case) for case in cases]
    if len(rows) != 3:
        raise ValueError("expected exactly three committed ambiguous evidence spans")
    record: dict[str, Any] = {
        "auditVersion": AUDIT_VERSION,
        "artifactRole": "development_only_offline_ambiguous_evidence_anchor_feasibility_audit",
        "providerCalls": 0,
        "networkCalls": 0,
        "historicalOutputMutation": False,
        "liveContractModified": False,
        "cases": rows,
        "aggregate": {
            "ambiguousAuthenticEvidenceSpanCount": len(rows),
            "uniqueLocatorAnchorCount": sum("minimumUniqueLocatorAnchor" in row for row in rows),
            "allCasesRecoverableWithExactLocatorAnchors": all(
                row.get("locatorAnchorVerification", {}).get("deterministicCoordinatesRecoverableFromUniqueAnchor")
                for row in rows
            ),
            "allCasesAvoidCurrentCoordinateGuide": all(
                not row.get("locatorAnchorVerification", {}).get("usesCoordinateGuide", True)
                for row in rows
            ),
            "semanticEvidenceExtensionEstablishedCount": 0,
            "semanticEvidenceExtensionDecision": "not_established_fail_closed_for_all_cases",
        },
        "conclusion": {
            "exactTextLocatorMechanismFeasible": "yes_for_these_three_historic_cases",
            "fullCoordinateGuideNeededForTheseThreeLocatorCases": "no_for_location_only",
            "notEstablished": "a semantic evidence-span extension or live contract choice",
            "failClosedBoundary": "a future mechanism must reject any span lacking a unique exact anchor",
        },
    }
    record["auditSha256"] = sha256_bytes(canonical_json(record))
    return record


def render_report(audit: Mapping[str, Any]) -> str:
    """Render concise findings while retaining the full literal only in JSON evidence rows."""

    lines = [
        "# Ambiguous evidence exact-anchor feasibility audit", "",
        "Offline only; no historic output or live contract was changed.", "",
        "| Span | Occurrences | Original cp | Unique anchor cp | Added left/right cp | Anchor unique | Structural line unique | Semantic extension |",
        "| --- | ---: | ---: | ---: | ---: | --- | --- | --- |",
    ]
    for row in audit["cases"]:
        anchor = row["minimumUniqueLocatorAnchor"]
        semantic = row["semanticEvidenceExtension"]
        lines.append(
            f"| {row['developmentID']} {row['evidenceSpanID']} | {row['exactOccurrenceCount']} | "
            f"{row['originalCodePointLength']} | {anchor['anchorCodePointLength']} | "
            f"{anchor['addedLeftCodePoints']}/{anchor['addedRightCodePoints']} | yes | "
            f"{str(semantic['canBecomeUniqueAsStructuralExactLine']).lower()} | not established (fail closed) |"
        )
    lines.extend([
        "", "All three historic ambiguous spans admit a unique exact locator anchor without normalization, fuzzy matching, the coordinate guide, or model-generated offsets. This establishes location-only feasibility, not a semantic-extension or live-contract decision.", "",
    ])
    return "\n".join(lines)


def write_audit(output_dir: Path = DEFAULT_OUTPUT_DIR) -> dict[str, Any]:
    """Write canonical machine-readable and concise Markdown audit forms."""

    audit = build_audit()
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "publication_ambiguous_evidence_anchor_feasibility_audit.json").write_bytes(canonical_json_file(audit))
    (output_dir / "publication_ambiguous_evidence_anchor_feasibility_report.md").write_text(render_report(audit), encoding="utf-8")
    return audit


def main(argv: Sequence[str] | None = None) -> int:
    """Execute the strictly offline anchor audit."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    audit = write_audit(parser.parse_args(argv).output_dir)
    print({"auditSha256": audit["auditSha256"], "providerCalls": 0})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
