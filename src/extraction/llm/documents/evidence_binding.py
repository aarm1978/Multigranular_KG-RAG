"""Bounded Hub literal binding under frozen Step 11 v0.3 §§2.2–2.3/5.1.

Replay only the accepted in-memory reader to verify supplied unit provenance and
visibility. Reuse the unchanged Publication literal binder, not its pipeline.
This module performs no semantic validation, graph acceptance or external IO.
"""

from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from typing import Any, Mapping

from src.extraction.llm.documents.source_units import read_page_source_units
from src.extraction.llm.publications.deterministic_evidence_binding import bind_evidence_spans


def _line(text: str, offset: int) -> int:
    """Use the reader's original splitlines convention without changing text."""
    start = 0
    for number, line in enumerate(text.splitlines(keepends=True), 1):
        if offset < start + len(line):
            return number
        start += len(line)
    return max(1, len(text.splitlines(keepends=True)))


def bind_hub_evidence(
    page: Mapping[str, Any], reader_result: Mapping[str, Any], source_unit_id: str,
    evidence_spans: list[Any], *, accepted_page_id: str,
    accepted_section_mapping: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Bind quotes to one trusted, successfully read static-visible Hub unit.

    The page, reader result, accepted Phase B page ID and optional accepted Section
    mapping are pipeline-owned inputs, never model-authored. Section mapping uses
    the accepted reader's format; a non-null Section in the supplied unit requires
    the same verified mapping on replay. Page identity follows the existing Phase
    B ID rule (first 20 SHA-256 hex characters of canonical_url).

    Only evidenceText and optional locatorAnchor are permitted in quotation input.
    Missing/ambiguous quotes fail without repair. Fenced snippets are held as
    possible Example context, with no bound semantic evidence. Reader replay
    verifies authority hashes, full unit metadata, original slices and visibility;
    it reads no files. It does not independently verify file_sha256/acquisition.

    Known replay warnings outside the selected unit do not block it. Additional
    unit/range warnings do; unscoped additional warnings fail closed. No global
    reviewRequired flag alone overrides an unaffected, reproducibly visible unit.
    """
    result: dict[str, Any] = {"status": "pending", "evidenceSpans": [],
                              "originalEvidence": deepcopy(evidence_spans), "diagnostics": []}
    failed = "failed_source_or_evidence_binding"

    def stop(status: str, reason: str) -> dict[str, Any]:
        """Keep technical failure, review and literal binding distinct."""
        result["status"] = status
        result["diagnostics"].append({"status": status, "reason": reason,
                                      "sourceUnitID": source_unit_id, "acceptedPageID": accepted_page_id})
        return result

    if not isinstance(page, Mapping) or not isinstance(reader_result, Mapping):
        return stop(failed, "trusted_source_missing_or_malformed")
    if reader_result.get("status") != "source_read_success":
        result["diagnostics"].extend(deepcopy(reader_result.get("diagnostics", []))
                                    if isinstance(reader_result.get("diagnostics"), list) else [])
        return stop(failed, "source_read_not_successful")
    url = page.get("canonical_url")
    if not isinstance(url, str):
        return stop(failed, "page_identity_malformed")
    try:
        expected_id = "hub:page:" + hashlib.sha256(url.encode("utf-8")).hexdigest()[:20]
    except UnicodeEncodeError:
        return stop(failed, "page_identity_malformed")
    if accepted_page_id != expected_id or page.get("page_key") != "hub-page:" + url:
        return stop(failed, "accepted_page_identity_mismatch")
    replay = read_page_source_units(page, accepted_section_mapping=accepted_section_mapping)
    if replay["status"] != "source_read_success":
        result["diagnostics"].extend(deepcopy(replay["diagnostics"]))
        return stop(failed, "authority_verification_failed")
    if reader_result.get("authority") != replay["authority"]:
        return stop(failed, "authority_provenance_mismatch")
    units = reader_result.get("sourceUnits")
    diagnostics = reader_result.get("diagnostics")
    if not isinstance(units, list) or not isinstance(diagnostics, list):
        return stop(failed, "reader_result_malformed")
    selected = [u for u in units if isinstance(u, Mapping) and u.get("sourceUnitID") == source_unit_id]
    if len(selected) != 1:
        return stop(failed, "source_unit_missing_or_ambiguous")
    unit = selected[0]
    text = page["content_mdx"]
    start, end = unit.get("startOffsetInAuthority"), unit.get("endOffsetInAuthority")
    if (type(start) is not int or type(end) is not int or not 0 <= start < end <= len(text)
            or unit.get("text") != text[start:end]
            or unit.get("startLine") != _line(text, start) or unit.get("endLine") != _line(text, end - 1)):
        return stop(failed, "source_unit_coordinates_or_provenance_mismatch")
    identity = json.dumps([page["page_key"], page["content_sha256"], start, end, unit.get("contentKind")], separators=(",", ":"))
    if source_unit_id != "hub:unit:" + hashlib.sha256(identity.encode("utf-8")).hexdigest():
        return stop(failed, "source_unit_identity_mismatch")
    verified = [u for u in replay["sourceUnits"] if u["sourceUnitID"] == source_unit_id]
    if len(verified) != 1:
        return stop("needs_review", "unit_not_reproducibly_visible")
    if unit != verified[0]:
        if unit.get("eligibility") != verified[0]["eligibility"]:
            return stop("needs_review", "unit_eligibility_unverified")
        return stop(failed, "source_unit_coordinates_or_provenance_mismatch")
    if unit["contentKind"] == "fenced_snippet" or unit["eligibility"] == "possible_example_context":
        return stop("needs_review", "possible_example_context_only")
    if (unit["eligibility"] != "static_visible_context"
            or unit["contentKind"] not in {"heading", "prose", "list_text", "table_text", "component_text"}):
        return stop("needs_review", "unit_not_static_visible")
    for diagnostic in diagnostics:
        if not isinstance(diagnostic, Mapping):
            return stop(failed, "reader_diagnostic_malformed")
        if diagnostic.get("status") == failed:
            result["diagnostics"].append(deepcopy(diagnostic))
            return stop(failed, "source_failure_diagnostic")
        if diagnostic.get("status") != "needs_review":
            return stop("needs_review", "unrecognized_source_diagnostic")
        unit_ref = diagnostic.get("sourceUnitID")
        first = diagnostic.get("startLine", diagnostic.get("sourceLine"))
        last = diagnostic.get("endLine", first)
        scoped_line = type(first) is int and type(last) is int and 1 <= first <= last
        affects = unit_ref == source_unit_id or scoped_line and first <= unit["endLine"] and last >= unit["startLine"]
        unknown_scope = (unit_ref is None and not scoped_line and diagnostic not in replay["diagnostics"])
        if affects or unknown_scope:
            result["diagnostics"].append(deepcopy(diagnostic))
            return stop("needs_review", "unit_visibility_requires_review")
    if (not isinstance(evidence_spans, list) or not evidence_spans
            or any(not isinstance(span, Mapping) or set(span) - {"evidenceText", "locatorAnchor"}
                   for span in evidence_spans)):
        return stop(failed, "invalid_or_model_authored_evidence_metadata")
    bound, report = bind_evidence_spans({"evidenceSpans": evidence_spans}, {
        "text": unit["text"], "startOffsetInDocument": unit["startOffsetInAuthority"],
        "canonicalArtifactID": accepted_page_id, "sourceUnitID": source_unit_id,
        "textHash": hashlib.sha256(unit["text"].encode("utf-8")).hexdigest(),
        "sectionID": unit["sectionID"], "sectionTitleRaw": unit["headingContext"],
    })
    result["bindingReport"] = report
    if report["bindingStatus"] != "bound":
        return stop(failed, "evidence_quote_unbound")
    provenance = {key: deepcopy(value) for key, value in replay["authority"].items() if key != "text"}
    for span in bound["evidenceSpans"]:
        start, end = span["startOffsetInDocument"], span["endOffsetInDocument"]
        result["evidenceSpans"].append({
            **provenance, **span, "startOffsetInAuthority": start, "endOffsetInAuthority": end,
            "startLine": _line(page["content_mdx"], start), "endLine": _line(page["content_mdx"], end - 1),
        })
    result["status"] = "evidence_bound"
    return result
