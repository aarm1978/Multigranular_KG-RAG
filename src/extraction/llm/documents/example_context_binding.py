"""Literal displayed-fence context only; never an accepted Hub Example."""

from __future__ import annotations

from copy import deepcopy
import hashlib
from typing import Any, Mapping

from src.extraction.llm.documents.evidence_binding import bind_hub_evidence, _line
from src.extraction.llm.documents.source_units import read_page_source_units
from src.extraction.llm.publications.deterministic_evidence_binding import bind_evidence_spans


def bind_example_context(
    page: Mapping[str, Any], reader_result: Mapping[str, Any], source_unit_id: str,
    evidence_spans: list[Any], *, accepted_page_id: str,
    accepted_section_mapping: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Bind only literal text in a reproducibly visible, closed fenced unit.

    The unchanged procedural binder verifies authority, page ID, exact unit and
    Section lineage, then holds fenced snippets. Only that specific hold permits
    this separate context path. Review diagnostics are still enforced. No code
    interpretation or parent acceptance occurs; all parent gates remain pending.
    """
    verification = bind_hub_evidence(page, reader_result, source_unit_id, evidence_spans,
        accepted_page_id=accepted_page_id, accepted_section_mapping=accepted_section_mapping)
    result: dict[str, Any] = {"status": "needs_review", "disposition": "possible_example_context",
        "evidenceSpans": [], "originalEvidence": deepcopy(evidence_spans), "diagnostics": [],
        "semanticStatus": "not_evaluated", "kgAuthorization": False,
        "pendingGates": ["accepted_procedure_or_step_parent", "accepted_required_parent_relations",
                         "independent_parent_and_dependent_evidence"]}

    def stop(status: str, reason: str) -> dict[str, Any]:
        """Keep source failures and review separate from literal-context success."""
        result["status"] = status
        result["diagnostics"].append({"status": status, "reason": reason, "sourceUnitID": source_unit_id})
        return result

    if not (verification["status"] == "needs_review" and verification["diagnostics"]
            and verification["diagnostics"][-1]["reason"] == "possible_example_context_only"):
        result["diagnostics"] = deepcopy(verification["diagnostics"])
        return stop(verification["status"] if verification["status"] != "evidence_bound" else "needs_review",
                    "not_verified_fenced_example_context")
    unit = next(u for u in reader_result["sourceUnits"] if isinstance(u, Mapping) and u.get("sourceUnitID") == source_unit_id)
    replay = read_page_source_units(page, accepted_section_mapping=accepted_section_mapping)
    result["sourceDiagnostics"] = deepcopy(reader_result["diagnostics"])
    for diagnostic in reader_result["diagnostics"]:
        if not isinstance(diagnostic, Mapping):
            return stop("failed_source_or_evidence_binding", "reader_diagnostic_malformed")
        ref = diagnostic.get("sourceUnitID")
        first = diagnostic.get("startLine", diagnostic.get("sourceLine"))
        last = diagnostic.get("endLine", first)
        scoped = type(first) is int and type(last) is int and 1 <= first <= last
        affects = ref == source_unit_id or scoped and first <= unit["endLine"] and last >= unit["startLine"]
        unknown = ref is None and not scoped and diagnostic not in replay["diagnostics"]
        if affects or unknown:
            result["diagnostics"].append(deepcopy(diagnostic))
            return stop("failed_source_or_evidence_binding" if diagnostic.get("status") == "failed_source_or_evidence_binding"
                        else "needs_review", "context_visibility_or_source_requires_review")
    if (not isinstance(evidence_spans, list) or not evidence_spans or any(not isinstance(s, Mapping)
            or set(s) - {"evidenceText", "locatorAnchor"} for s in evidence_spans)):
        return stop("failed_source_or_evidence_binding", "invalid_or_model_authored_evidence_metadata")
    bound, report = bind_evidence_spans({"evidenceSpans": evidence_spans}, {
        "text": unit["text"], "startOffsetInDocument": unit["startOffsetInAuthority"],
        "canonicalArtifactID": accepted_page_id, "sourceUnitID": source_unit_id,
        "textHash": hashlib.sha256(unit["text"].encode()).hexdigest(),
        "sectionID": unit["sectionID"], "sectionTitleRaw": unit["headingContext"]})
    result["bindingReport"] = report
    if report["bindingStatus"] != "bound":
        return stop("failed_source_or_evidence_binding", "evidence_quote_unbound")
    metadata = {k: deepcopy(v) for k, v in replay["authority"].items() if k != "text"}
    for span in bound["evidenceSpans"]:
        lo, hi = span["startOffsetInDocument"], span["endOffsetInDocument"]
        result["evidenceSpans"].append({**metadata, **span, "startOffsetInAuthority": lo,
            "endOffsetInAuthority": hi, "startLine": _line(page["content_mdx"], lo),
            "endLine": _line(page["content_mdx"], hi - 1), "eligibility": "possible_example_context"})
    result["status"] = "example_context_bound"
    return result
