"""Opt-in transport projection; the complete GitHub request remains replay authority."""
from copy import deepcopy
import hashlib
import json
from collections import Counter
from typing import Any

PROJECTION_VERSION = "github-provider-input/1.0.0"
WAVE_B_PROJECTION_VERSION = "github-provider-input/1.1.0"
WAVE_C_PROJECTION_VERSION = "github-provider-input/1.2.0"
# Only known reader metadata can be omitted. Unknown fields/reasons stay visible.
AUDIT_FIELDS = frozenset({
    "artifactFamily", "repo_id", "full_name", "frozenCommitSha", "contractID",
    "canonicalArtifactID", "path", "selection_reason", "file_role", "extension",
    "rawFileSha256", "authorityKind", "rawIntegrityStatus", "decodePolicy",
    "cellIndex", "status", "reason", "startLine", "endLine",
    "startOffsetInAuthority", "endOffsetInAuthority", "sourceUnitID",
})


def _bytes(value: Any, *, ascii_only: bool = False) -> bytes:
    """Serialize exact JSON values without changing source strings."""
    return json.dumps(value, ensure_ascii=ascii_only, sort_keys=True,
                      separators=(",", ":"), allow_nan=False).encode("utf-8")


def _disjoint(row: dict, units: list[dict]) -> bool:
    """Prove disjointness conservatively; absent/ambiguous coordinates stay visible."""
    if "sourceUnitID" in row:
        return False  # Conflicting explicit locators must remain visible.
    path = row.get("path")
    if not isinstance(path, str) or not path:
        return False
    matches = [u for u in units if u.get("path") == path]
    if not matches:
        return True
    if "cellIndex" in row:
        cell = row["cellIndex"]
        if cell is not None and (type(cell) is not int or cell < 0):
            return False
        # None on a notebook can mean a file-wide warning, not a cell locator.
        if cell is not None:
            matches = [u for u in matches if u.get("cellIndex") == cell]
            if not matches:
                return True
    if any(u.get("cellIndex") is not None for u in matches) and row.get("cellIndex") is None:
        return False
    start, end = row.get("startOffsetInAuthority"), row.get("endOffsetInAuthority")
    if type(start) is not int or type(end) is not int or not 0 <= start < end:
        return False
    return all(end <= u["startOffsetInAuthority"] or start >= u["endOffsetInAuthority"] for u in matches)


def _project_audit(rows: list, units: list[dict]) -> tuple[list, dict]:
    """Keep every failure and potentially selected warning; count omitted audit metadata."""
    retained, omitted = [], []
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("projection_audit_record_malformed")
        status, reason = row.get("status"), row.get("reason")
        known = not (set(row) - AUDIT_FIELDS)
        ordinary = (status, reason) in {
            ("source_read_success", "authority_recorded"),
            ("source_read_success", "notebook_json_read"),
            ("excluded", "non_prose_file_type"),
            ("excluded", "administrative_or_machine_file"),
            ("skipped_duplicate", "phase_a_readme_authority"),
        }
        scoped_review = (status == "needs_review"
                         and reason == "content_kind_or_purpose_requires_review"
                         and _disjoint(row, units))
        if known and (ordinary or scoped_review):
            omitted.append(row)
        else:
            retained.append(deepcopy(row))
    counts = Counter((r.get("status"), r.get("reason")) for r in omitted)
    summary = {"originalCount": len(rows), "retainedCount": len(retained),
               "omittedCount": len(omitted),
               "originalRecordsSha256": hashlib.sha256(_bytes(rows, ascii_only=True)).hexdigest(),
               "omittedStatusReasonCounts": [
                   {"status": status, "reason": reason, "count": count}
                   for (status, reason), count in sorted(counts.items(), key=lambda pair: str(pair[0]))]}
    return retained, summary


def project_provider_input(request_result: dict, *, version: str) -> dict:
    """Project a trusted ready request only on explicit version selection.

    No source read, semantic validation, provider call or replay occurs. Full
    semantic bytes and their original digest are returned alongside distinct exact
    provider bytes. Selected text/metadata and all semantic restrictions are copied
    unchanged. Completeness booleans never change; omissions summarize audit metadata
    only, never scientific text. Global/unknown warnings and all failures survive.
    """
    if not isinstance(version, str) or version not in (PROJECTION_VERSION, WAVE_B_PROJECTION_VERSION, WAVE_C_PROJECTION_VERSION):
        raise ValueError("unsupported_provider_input_projection")
    if not isinstance(request_result, dict) or request_result.get("status") != "request_ready":
        raise ValueError("projection_requires_ready_request")
    expected_request_version = {PROJECTION_VERSION: "github-request/1.0.0",
        WAVE_B_PROJECTION_VERSION: "github-request/1.1.0", WAVE_C_PROJECTION_VERSION: "github-request/1.2.0"}[version]
    body = request_result.get("request")
    if not isinstance(body, dict) or body.get("artifactFamily") != "github" or body.get("schemaVersion") != expected_request_version:
        raise ValueError("projection_request_contract_mismatch")
    if version in (WAVE_B_PROJECTION_VERSION, WAVE_C_PROJECTION_VERSION):
        from src.extraction.llm.coderepos.request_contract import parse_recorded_response, RESPONSE_VERSION
        check = parse_recorded_response(_bytes({"schemaVersion": RESPONSE_VERSION,
            "candidateNodes": [], "candidateEdges": [], "abstentions": []}), request=request_result)
        if check["status"] == "processing_failed":
            raise ValueError("projection_prompt_variant_mismatch")
    semantic = _bytes(body, ascii_only=True)
    digest = hashlib.sha256(semantic).hexdigest()
    if request_result.get("requestSha256") != digest:
        raise ValueError("semantic_request_digest_mismatch")
    units, ids = body.get("sourceUnits"), body.get("selectedSourceUnitIDs")
    if (not isinstance(units, list) or not units or not isinstance(ids, list)
            or any(not isinstance(u, dict) or not isinstance(u.get("text"), str)
                   or u.get("contentKind") != "prose" for u in units)
            or [u.get("sourceUnitID") for u in units] != ids
            or any(not isinstance(uid, str) for uid in ids) or len(set(ids)) != len(ids)):
        raise ValueError("projection_selection_malformed")
    completeness = body.get("sourceCompleteness")
    if (not isinstance(completeness, dict) or not isinstance(completeness.get("reads"), list)
            or not isinstance(body.get("sourceDiagnostics"), list)):
        raise ValueError("projection_audit_malformed")
    result = deepcopy(body)
    result["sourceDiagnostics"], diagnostics = _project_audit(body["sourceDiagnostics"], units)
    result["sourceCompleteness"]["reads"], reads = _project_audit(completeness["reads"], units)
    result["providerInputProjection"] = {
        "schemaVersion": version, "semanticRequestSha256": digest,
        "sourceDiagnostics": diagnostics, "sourceReads": reads,
        "boundary": "Only selected sourceUnits are evidence. Omitted read/audit metadata remains in the full trusted semantic request; completeness flags are unchanged. Omitted warnings are not semantic no-evidence or accepted outcomes."}
    provider = _bytes(result)
    return {"projectionVersion": version, "semanticRequestSha256": digest,
            "semanticRequestBytes": semantic, "providerInputSha256": hashlib.sha256(provider).hexdigest(),
            "inputBytes": provider}
