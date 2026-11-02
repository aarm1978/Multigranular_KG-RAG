"""In-memory GitHub literal binding; frozen Step 11 v0.3 §§2/4, no semantics."""

from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from pathlib import PurePosixPath
import re
from typing import Any, Mapping

from src.extraction.llm.coderepos.source_units import ADMIN_NAME, CONTRACT_ID, REASONS, TEXT_EXTENSIONS, _line, _passages, _safe_path
from src.extraction.llm.publications.deterministic_evidence_binding import bind_evidence_spans


def bind_repository_evidence(
    reader_result: Mapping[str, Any], source_unit_id: str, evidence_spans: list[Any], *,
    accepted_repository: Mapping[str, Any],
) -> dict[str, Any]:
    """Bind to one caller-trusted eligible reader unit without rereading files.

    accepted_repository independently supplies canonicalArtifactID, repo_id,
    full_name, frozenCommitSha. Reader metadata is pipeline-owned, never a model
    claim. Verify authority text/hash, unit slice/identity and prose selection.
    Changelog/contributing eligibility uses the reader's trusted passageReview,
    never a model-supplied gate. Newly computed hashes do not verify acquisition.

    Technical/review diagnostics block only their path/cell/span, or all units
    when scope is unknown. This is source-level isolation, not candidate processing.
    """
    result: dict[str, Any] = {"status": "pending", "evidenceSpans": [], "diagnostics": [],
        "originalEvidence": deepcopy(evidence_spans), "semanticStatus": "not_evaluated", "kgAuthorization": False}
    failed = "failed_source_or_evidence_binding"

    def stop(status: str, reason: str) -> dict[str, Any]:
        """Return the precise source/binding/review failure without repairing input."""
        result["status"] = status
        result["diagnostics"].append({"status": status, "reason": reason, "sourceUnitID": source_unit_id})
        return result

    if not isinstance(reader_result, Mapping) or not isinstance(accepted_repository, Mapping):
        return stop(failed, "trusted_source_missing_or_malformed")
    if any(not isinstance(reader_result.get(k), list) for k in ("sourceUnits", "authorities", "reads", "diagnostics")):
        return stop(failed, "reader_result_malformed")
    selected = [u for u in reader_result["sourceUnits"] if isinstance(u, Mapping) and u.get("sourceUnitID") == source_unit_id]
    if len(selected) != 1:
        return stop(failed, "source_unit_missing_or_ambiguous")
    unit = selected[0]
    keys = ("canonicalArtifactID", "repo_id", "full_name", "frozenCommitSha")
    if (any(k not in accepted_repository or unit.get(k) != accepted_repository[k] for k in keys)
            or type(unit.get("repo_id")) is not int or unit.get("canonicalArtifactID") != f"github:repo:{unit.get('repo_id')}"
            or unit.get("artifactFamily") != "github" or unit.get("contractID") != CONTRACT_ID
            or not isinstance(unit.get("frozenCommitSha"), str) or not re.fullmatch(r"[0-9a-fA-F]{40}", unit["frozenCommitSha"])
            or not _safe_path(unit.get("path")) or not _safe_path(unit.get("full_name"))):
        return stop(failed, "trusted_owner_or_provenance_mismatch")
    path, cell = unit["path"], unit.get("cellIndex")
    suffix, filename = PurePosixPath(path).suffix.lower(), PurePosixPath(path).name.lower()
    if unit.get("authorityKind") == "phase_a_readme":
        eligible = cell is None and filename.startswith("readme") and suffix in TEXT_EXTENSIONS | {""}
    elif unit.get("authorityKind") == "downloaded_file":
        eligible = (unit.get("selection_reason") in REASONS
            and isinstance(unit.get("extension"), str) and unit["extension"].lower() == suffix
            and (suffix == ".ipynb" and type(cell) is int and cell >= 0 or cell is None
                 and (suffix in TEXT_EXTENSIONS or not suffix and filename in {"readme", "citation"})))
        if not isinstance(unit.get("rawFileSha256"), str) or not re.fullmatch(r"[0-9a-f]{64}", unit["rawFileSha256"]):
            return stop(failed, "raw_file_provenance_missing_or_malformed")
    else:
        eligible = False
    if ADMIN_NAME.match(filename) or any(p.lower() in {".github", ".git"} for p in path.split("/")):
        eligible = False
    if not eligible or unit.get("eligibility") != "prose_candidate" or unit.get("contentKind") != "prose":
        return stop("needs_review", "source_not_eligible_prose")

    def same(row: Any) -> bool:
        """Match one authority/read record by original case-sensitive file and cell."""
        return isinstance(row, Mapping) and row.get("path") == path and row.get("cellIndex") == cell

    authorities = [a for a in reader_result["authorities"] if same(a)]
    if len(authorities) != 1:
        return stop(failed, "authority_missing_or_ambiguous")
    authority = authorities[0]
    text = authority.get("text")
    if not isinstance(text, str) or any(unit.get(k) != v for k, v in authority.items() if k != "text"):
        return stop(failed, "authority_metadata_mismatch")
    try:
        digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
    except UnicodeEncodeError:
        return stop(failed, "authority_text_malformed")
    start, end = unit.get("startOffsetInAuthority"), unit.get("endOffsetInAuthority")
    if (digest != authority.get("authorityTextSha256") or type(start) is not int or type(end) is not int
            or not 0 <= start < end <= len(text) or text[start:end] != unit.get("text")):
        return stop(failed, "source_content_integrity_failure")
    identity = json.dumps([unit["repo_id"], unit["full_name"], unit["frozenCommitSha"], path, cell, digest, start, end],
                          separators=(",", ":"), ensure_ascii=True)
    if (source_unit_id != "github:unit:" + hashlib.sha256(identity.encode()).hexdigest()
            or unit.get("startLine") != _line(text, start) or unit.get("endLine") != _line(text, end - 1)):
        return stop(failed, "source_unit_coordinates_or_identity_mismatch")
    spans, _ = _passages(text)
    if filename.startswith(("changelog", "contributing")):
        review = unit.get("passageReview")
        purposes = {"scientific_operational_procedure"} if filename.startswith("contributing") else {"descriptive_change", "version_statement"}
        if (not isinstance(review, Mapping) or review.get("authorityTextSha256") != digest
                or review.get("startOffsetInAuthority") != start or review.get("endOffsetInAuthority") != end
                or review.get("purpose") not in purposes or not isinstance(review.get("reviewID"), str)
                or not review["reviewID"].strip()):
            return stop("needs_review", "passage_eligibility_unverified")
        visible = any(a <= start < end <= b and h == unit.get("headingContext") for a, b, h in spans)
    else:
        visible = (start, end, unit.get("headingContext")) in spans
    if not visible:
        return stop("needs_review", "unit_not_reproducibly_prose")
    if not any(same(r) and r.get("status") == "source_read_success" and r.get("reason") == "authority_recorded"
               for r in reader_result["reads"]):
        return stop(failed, "successful_source_read_missing")
    result["sourceDiagnostics"] = deepcopy(reader_result["diagnostics"])
    for diagnostic in reader_result["diagnostics"]:
        if not isinstance(diagnostic, Mapping):
            return stop(failed, "reader_diagnostic_malformed")
        if diagnostic.get("path") is not None and diagnostic["path"] != path:
            continue
        if diagnostic.get("cellIndex") is not None and diagnostic["cellIndex"] != cell:
            continue
        ref = diagnostic.get("sourceUnitID")
        lo, hi = diagnostic.get("startOffsetInAuthority"), diagnostic.get("endOffsetInAuthority")
        first, last = diagnostic.get("startLine"), diagnostic.get("endLine")
        if ref is not None:
            affects = ref == source_unit_id
        elif type(lo) is int and type(hi) is int and 0 <= lo < hi <= len(text):
            affects = lo < end and hi > start
        elif type(first) is int and type(last) is int and 1 <= first <= last:
            affects = first <= unit["endLine"] and last >= unit["startLine"]
        else:
            affects = True
        if affects:
            result["diagnostics"].append(deepcopy(diagnostic))
            return stop(failed if diagnostic.get("status") == failed else "needs_review", "source_diagnostic_affects_unit")
    if (not isinstance(evidence_spans, list) or not evidence_spans or any(not isinstance(s, Mapping)
            or set(s) - {"evidenceText", "locatorAnchor"} for s in evidence_spans)):
        return stop(failed, "invalid_or_model_authored_evidence_metadata")
    bound, report = bind_evidence_spans({"evidenceSpans": evidence_spans}, {
        "text": unit["text"], "startOffsetInDocument": start, "canonicalArtifactID": unit["canonicalArtifactID"],
        "sourceUnitID": source_unit_id, "textHash": hashlib.sha256(unit["text"].encode()).hexdigest(),
        "sectionID": None, "sectionTitleRaw": unit.get("headingContext")})
    result["bindingReport"] = report
    if report["bindingStatus"] != "bound":
        return stop(failed, "evidence_quote_unbound")
    metadata = {k: deepcopy(v) for k, v in unit.items() if k != "text"}
    for span in bound["evidenceSpans"]:
        lo, hi = span["startOffsetInDocument"], span["endOffsetInDocument"]
        result["evidenceSpans"].append({**metadata, **span, "startOffsetInAuthority": lo,
            "endOffsetInAuthority": hi, "startLine": _line(text, lo), "endLine": _line(text, hi - 1)})
    result["status"] = "evidence_bound"
    return result
