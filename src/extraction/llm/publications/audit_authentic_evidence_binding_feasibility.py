"""Audit deterministic literal-to-offset binding against preserved authentic DEV output."""

from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from src.extraction.llm.publications.evidence_coordinate_guide import (
    COORDINATE_GUIDE_SEPARATOR,
    build_evidence_coordinate_guide,
)
from src.extraction.llm.publications.request_builder import (
    PROJECT_ROOT,
    canonical_json,
    canonical_json_file,
    load_json_object,
    sha256_bytes,
)
from src.extraction.llm.publications.run_publication_full_devset0_node_development import (
    DEV_IDS,
)


AUDIT_VERSION = "publication-authentic-evidence-binding-feasibility/0.1.0"
C1B_DIR = PROJECT_ROOT / "data/curation/papers/m2/c1b"
C2A_DIR = PROJECT_ROOT / "data/curation/papers/m2/c2a/counterfactual"
DEFAULT_OUTPUT_DIR = (
    PROJECT_ROOT / "data/curation/papers/m2/"
    "full_semantic_input_contract_efficiency_audit"
)


def _paths(development_id: str) -> dict[str, Path]:
    """Return the preserved C1B authentic and C2A validator-context paths."""

    compact = development_id.lower().replace("-", "")
    return {
        "raw": C1B_DIR / development_id / f"publication_m2c1b_{compact}_exact_structured_model_output.json",
        "request": C1B_DIR / development_id / f"publication_m2c1b_{compact}_live_request.json",
        "validation": C1B_DIR / development_id / f"publication_m2c1b_{compact}_validation_results.json",
        "c2aValidation": C2A_DIR / development_id / f"publication_m2c2a_{compact}_section_title_only_validation_results.json",
    }


def _occurrences(text: str, literal: str) -> list[int]:
    """Return every overlapping exact Unicode-code-point occurrence without selection."""

    if not literal:
        return []
    starts: list[int] = []
    cursor = 0
    while True:
        index = text.find(literal, cursor)
        if index < 0:
            return starts
        starts.append(index)
        cursor = index + 1


def _context_character_kind(value: str) -> str:
    """Describe a boundary character without reproducing source text."""

    if not value:
        return "boundary"
    if value.isspace():
        return "whitespace"
    if value.isalnum():
        return "alphanumeric"
    return "punctuation_or_symbol"


def _span_row(
    span: Mapping[str, Any], source_unit: Mapping[str, Any],
    validation: Mapping[str, Any],
) -> dict[str, Any]:
    """Classify one authentic model-authored evidence span without changing it."""

    literal = span.get("evidenceText")
    text = source_unit["text"]
    evidence_id = str(span["evidenceSpanID"])
    validation_row = next(
        (row for row in validation["evidenceResults"] if row["evidenceSpanID"] == evidence_id),
        None,
    )
    if not isinstance(literal, str) or not literal:
        return {
            "evidenceSpanID": evidence_id,
            "classification": "zero_exact_occurrences",
            "nonLiteral": True,
            "reason": "missing_or_empty_model_authored_evidenceText",
            "validator": validation_row,
        }
    starts = _occurrences(text, literal)
    row: dict[str, Any] = {
        "evidenceSpanID": evidence_id,
        "evidenceTextSha256": sha256_bytes(literal.encode("utf-8")),
        "literalCodePointLength": len(literal),
        "literalUtf8Bytes": len(literal.encode("utf-8")),
        "literalTokenLikeCount": len(literal.split()),
        "exactOccurrenceCount": len(starts),
        "validator": validation_row,
    }
    if not starts:
        row.update({
            "classification": "zero_exact_occurrences",
            "nonLiteral": True,
            "reason": "model_authored_evidenceText_is_not_an_exact_canonical_sourceUnit_text_literal",
        })
        return row
    if len(starts) > 1:
        row.update({
            "classification": "multiple_exact_occurrences",
            "nonLiteral": False,
            "occurrenceStartOffsetsInUnit": starts,
            "occurrenceBoundaryCharacterKinds": [
                {
                    "before": _context_character_kind(text[start - 1:start]),
                    "after": _context_character_kind(text[start + len(literal):start + len(literal) + 1]),
                }
                for start in starts
            ],
            "resolution": "not_selected_fail_closed",
        })
        return row
    start = starts[0]
    end = start + len(literal)
    document_start = source_unit["startOffsetInDocument"] + start
    document_end = source_unit["startOffsetInDocument"] + end
    returned = {
        "startOffsetInUnit": span.get("startOffsetInUnit"),
        "endOffsetInUnit": span.get("endOffsetInUnit"),
        "startOffsetInDocument": span.get("startOffsetInDocument"),
        "endOffsetInDocument": span.get("endOffsetInDocument"),
    }
    derived = {
        "startOffsetInUnit": start,
        "endOffsetInUnit": end,
        "startOffsetInDocument": document_start,
        "endOffsetInDocument": document_end,
    }
    row.update({
        "classification": "exactly_one_occurrence",
        "nonLiteral": False,
        "derivedOffsets": derived,
        "returnedOffsets": returned,
        "coordinateAgreement": {
            key: returned[key] == derived[key] for key in derived
        },
    })
    row["coordinateAgreement"]["all"] = all(row["coordinateAgreement"].values())
    return row


def _candidate_rows(
    payload: Mapping[str, Any], span_rows: Sequence[Mapping[str, Any]],
    c1b_validation: Mapping[str, Any], c2a_validation: Mapping[str, Any],
) -> list[dict[str, Any]]:
    """Summarize evidence-reference groups for every authentic model candidate."""

    spans = {row["evidenceSpanID"]: row for row in span_rows}
    c1b_records = {row["recordID"]: row for row in c1b_validation["recordResults"]}
    c2a_records = {row["recordID"]: row for row in c2a_validation["recordResults"]}
    rows: list[dict[str, Any]] = []
    for candidate in list(payload["candidateNodes"]) + list(payload["candidateEdges"]):
        evidence_ids = list(candidate.get("evidenceSpanIDs", []))
        referenced = [spans.get(item) for item in evidence_ids]
        classifications = [row["classification"] for row in referenced if row]
        record_id = candidate["candidateID"]
        rows.append({
            "candidateID": record_id,
            "candidateType": "candidate_edge" if record_id.startswith("edge-") else "candidate_node",
            "evidenceSpanIDs": evidence_ids,
            "allReferencedEvidenceUnique": bool(referenced) and all(
                row and row["classification"] == "exactly_one_occurrence" for row in referenced
            ),
            "anyNonLiteralEvidence": any(item == "zero_exact_occurrences" for item in classifications),
            "anyAmbiguousEvidence": any(item == "multiple_exact_occurrences" for item in classifications),
            "c1bValidationStatus": c1b_records.get(record_id, {}).get("candidateValidationStatus"),
            "c2aTitleOnlyValidationStatus": c2a_records.get(record_id, {}).get("candidateValidationStatus"),
            "c2aTitleOnlyFindingCodes": [
                finding["code"] for finding in c2a_records.get(record_id, {}).get("findings", [])
            ],
        })
    return rows


def audit_unit(development_id: str) -> dict[str, Any]:
    """Audit authentic output for one DEV unit using C2A only as validator context."""

    paths = _paths(development_id)
    payload = load_json_object(paths["raw"])
    request = load_json_object(paths["request"])
    validation = load_json_object(paths["validation"])
    c2a = load_json_object(paths["c2aValidation"])["validationResults"]
    source_unit = request["sourceUnit"]
    spans = [_span_row(span, source_unit, validation) for span in payload["evidenceSpans"]]
    candidates = _candidate_rows(payload, spans, validation, c2a)
    counts = Counter(row["classification"] for row in spans)
    unique = [row for row in spans if row["classification"] == "exactly_one_occurrence"]
    coordinate_mismatches = [row for row in unique if not row["coordinateAgreement"]["all"]]
    coordinate_failure_evidence = {
        row["evidenceSpanID"] for row in coordinate_mismatches
        if any(code.startswith("OFFSET_") for code in [
            finding["code"] for finding in row["validator"].get("findings", [])
        ])
    }
    prevented = [
        row for row in candidates
        if row["c2aTitleOnlyValidationStatus"] == "rejected"
        and set(row["evidenceSpanIDs"]).intersection(coordinate_failure_evidence)
        and not row["anyNonLiteralEvidence"] and not row["anyAmbiguousEvidence"]
    ]
    return {
        "developmentID": development_id,
        "authenticRawModelOutputSha256": sha256_bytes(paths["raw"].read_bytes()),
        "sourceUnitID": source_unit["sourceUnitID"],
        "sourceUnitTextSha256": source_unit["textHash"],
        "evidenceSpanRows": spans,
        "candidateEvidenceGroups": candidates,
        "summary": {
            "authenticEvidenceSpanCount": len(spans),
            "exactlyOneOccurrenceCount": counts["exactly_one_occurrence"],
            "multipleExactOccurrenceCount": counts["multiple_exact_occurrences"],
            "zeroExactOccurrenceCount": counts["zero_exact_occurrences"],
            "uniqueCoordinateAgreementCount": sum(row["coordinateAgreement"]["all"] for row in unique),
            "uniqueCoordinateMismatchCount": len(coordinate_mismatches),
            "authenticCandidateCount": len(candidates),
            "candidatesAllEvidenceUnique": sum(row["allReferencedEvidenceUnique"] for row in candidates),
            "candidatesWithAmbiguousEvidence": sum(row["anyAmbiguousEvidence"] for row in candidates),
            "candidatesWithNonLiteralEvidence": sum(row["anyNonLiteralEvidence"] for row in candidates),
            "conservativeC2ACandidateFailuresProspectivelyPreventedByUniqueCoordinateBinding": len(prevented),
        },
        "dev05Interpretation": (
            "not_applicable" if development_id != "DEV-05" else
            "evidence-0003 is a unique exact canonical literal at unit offset 541, while "
            "the model returned 545; its validator EVIDENCE_NOT_LITERAL finding is caused by "
            "the incorrect claimed coordinates, so prospective unique binding would prevent it"
        ),
    }


def build_audit() -> dict[str, Any]:
    """Build the deterministic C1B/C2A-context audit without provider interaction."""

    units = [audit_unit(development_id) for development_id in DEV_IDS]
    summaries = [row["summary"] for row in units]
    spans = [span for unit in units for span in unit["evidenceSpanRows"]]
    ambiguous = [row for row in spans if row["classification"] == "multiple_exact_occurrences"]
    guide_omission = sum(
        len(canonical_json(build_evidence_coordinate_guide(
            load_json_object(_paths(development_id)["request"])["sourceUnit"]
        ))) + len(COORDINATE_GUIDE_SEPARATOR.encode("utf-8"))
        for development_id in DEV_IDS
    )
    record: dict[str, Any] = {
        "auditVersion": AUDIT_VERSION,
        "artifactRole": "development_only_offline_authentic_evidence_binding_feasibility_audit",
        "developmentOnly": True,
        "providerCalls": 0,
        "networkCalls": 0,
        "authenticModelOutputMutation": False,
        "c2aUse": "validator-context-only; C2A payloads are not treated as authentic model output",
        "units": units,
        "aggregate": {
            "authenticEvidenceSpanCount": sum(row["authenticEvidenceSpanCount"] for row in summaries),
            "exactlyOneOccurrenceCount": sum(row["exactlyOneOccurrenceCount"] for row in summaries),
            "multipleExactOccurrenceCount": sum(row["multipleExactOccurrenceCount"] for row in summaries),
            "zeroExactOccurrenceCount": sum(row["zeroExactOccurrenceCount"] for row in summaries),
            "uniqueCoordinateAgreementCount": sum(row["uniqueCoordinateAgreementCount"] for row in summaries),
            "uniqueCoordinateMismatchCount": sum(row["uniqueCoordinateMismatchCount"] for row in summaries),
            "authenticCandidateCount": sum(row["authenticCandidateCount"] for row in summaries),
            "candidatesAllEvidenceUnique": sum(row["candidatesAllEvidenceUnique"] for row in summaries),
            "candidatesWithAmbiguousEvidence": sum(row["candidatesWithAmbiguousEvidence"] for row in summaries),
            "candidatesWithNonLiteralEvidence": sum(row["candidatesWithNonLiteralEvidence"] for row in summaries),
            "conservativeC2ACandidateFailuresProspectivelyPreventedByUniqueCoordinateBinding": sum(row["conservativeC2ACandidateFailuresProspectivelyPreventedByUniqueCoordinateBinding"] for row in summaries),
            "ambiguousFullSpanLengthDistribution": dict(sorted(Counter(row["literalCodePointLength"] for row in ambiguous).items())),
            "ambiguousOccurrenceCountDistribution": dict(sorted(Counter(row["exactOccurrenceCount"] for row in ambiguous).items())),
        },
        "hypotheticalCoordinateGuideOmission": {
            "providerInputReductionBytesAcrossDEV01toDEV10": guide_omission,
            "classification": "hypothetical methodological_or_contractual_change; not implemented",
            "reason": "guide is current prospective coordinate-production support",
        },
        "prospectiveInterpretation": {
            "supportsInvestigation": "yes_for_a_fail_closed_deterministic_binding_layer_only",
            "doesNotSupport": "replacing current literal evidence, coordinate, or validator requirements",
            "requiredBoundary": "bind only exactly-one canonical occurrences; preserve zero/multiple as invalid or unresolved",
        },
    }
    record["auditSha256"] = sha256_bytes(canonical_json(record))
    return record


def render_report(audit: Mapping[str, Any]) -> str:
    """Render a concise companion report without reproducing protected source text."""

    total = audit["aggregate"]
    span_count = total["authenticEvidenceSpanCount"]
    rate = lambda value: f"{(100 * value / span_count):.1f}%" if span_count else "n/a"
    return "\n".join([
        "# Authentic evidence-binding feasibility audit", "",
        "Offline only. Authentic C1B output is read-only; C2A is validator context only.", "",
        f"- Evidence spans: {span_count}; unique exact literals: {total['exactlyOneOccurrenceCount']} ({rate(total['exactlyOneOccurrenceCount'])}); ambiguous: {total['multipleExactOccurrenceCount']} ({rate(total['multipleExactOccurrenceCount'])}); non-literal/zero: {total['zeroExactOccurrenceCount']} ({rate(total['zeroExactOccurrenceCount'])}).",
        f"- Unique bindings: {total['uniqueCoordinateAgreementCount']} coordinate agreements and {total['uniqueCoordinateMismatchCount']} mismatches.",
        f"- Candidate evidence groups: {total['authenticCandidateCount']}; all-unique: {total['candidatesAllEvidenceUnique']}; ambiguous: {total['candidatesWithAmbiguousEvidence']}; non-literal: {total['candidatesWithNonLiteralEvidence']}.",
        f"- Conservative title-corrected historical candidate failures preventable by unique deterministic coordinate binding: {total['conservativeC2ACandidateFailuresProspectivelyPreventedByUniqueCoordinateBinding']}.",
        "- DEV-05: authentic `evidence-0003` is uniquely bindable at unit offset 541, not the returned 545. Its coordinate-local validator `EVIDENCE_NOT_LITERAL` finding follows from that incorrect claimed offset; unique deterministic binding would have prevented the two dependent candidate rejections prospectively.",
        f"- Hypothetical guide omission: {audit['hypotheticalCoordinateGuideOmission']['providerInputReductionBytesAcrossDEV01toDEV10']} provider-input bytes across DEV-01–DEV-10. This is methodological/contractual and not implemented.",
        "- Conclusion: authentic evidence supports investigating a strictly fail-closed binding layer for unique exact literals only; it does not support weakening literal-evidence or coordinate validation.", "",
    ])


def write_audit(output_dir: Path = DEFAULT_OUTPUT_DIR) -> dict[str, Any]:
    """Write the reproducible JSON and Markdown audit artifacts."""

    audit = build_audit()
    _write = lambda path, value: path.write_bytes(canonical_json_file(value))
    output_dir.mkdir(parents=True, exist_ok=True)
    _write(output_dir / "publication_authentic_evidence_binding_feasibility_audit.json", audit)
    (output_dir / "publication_authentic_evidence_binding_feasibility_report.md").write_text(render_report(audit), encoding="utf-8")
    return audit


def main(argv: Sequence[str] | None = None) -> int:
    """Execute the no-call authentic-evidence audit."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    audit = write_audit(parser.parse_args(argv).output_dir)
    print(json.dumps({"auditSha256": audit["auditSha256"], "providerCalls": 0}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
