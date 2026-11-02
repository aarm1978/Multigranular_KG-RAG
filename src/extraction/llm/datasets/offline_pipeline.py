"""Deterministic hydroshare replay of recorded responses; no provider or graph IO."""
from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
import hashlib
import json
from typing import Any, Mapping

from src.extraction.llm.datasets.request_contract import build_request, parse_recorded_response, CONTRACT_ID
from src.extraction.llm.datasets.candidate_validation import validate_dataset_candidates

REPLAY_VERSION = "hydroshare-offline-replay/1.0.0"


@dataclass(frozen=True)
class ReplayReport:
    """Immutable canonical report, digest and exact response bytes.

    to_record returns a detached inspection view. Editing that view cannot change
    the sealed report, subsequent views, caller inputs or any accepted artifacts.
    Bytes in the canonical JSON are explicitly hex-encoded, never decoded with
    replacement. No provider identity or execution metadata is inferred.
    """

    report_json: str
    report_sha256: str
    response_bytes: bytes | None

    def to_record(self) -> dict[str, Any]:
        """Return a fresh report view, restoring only the known raw-response slot."""
        result = json.loads(self.report_json)
        if result["responseInputType"] == "bytes":
            result["parseResult"]["originalResponse"] = self.response_bytes
        return result


def replay_recorded_response(recorded_response: bytes | str, *, request_inputs: Mapping[str, Any],
                             expected_request_sha256: str | None = None) -> ReplayReport:
    """Build, parse and validate one caller-selected frozen source context.

    request_inputs uses this family's accepted build_request signature. All inputs
    are snapshotted before construction. Optional expected_request_sha256 is the
    caller's independently supplied recorded-request digest; a mismatch stops
    replay. Without it, the report links supplied bytes to the rebuilt request,
    but does not claim an independently verified generation/provider association.

    Identifiable parse-invalid rows are quarantined unchanged. Only parse-clean,
    selected-unit-bound rows reach the unchanged batch validator. Actual local
    references remain unchanged, so missing rejected parents/path edges propagate
    through its existing dependency rules. No authentic payload is repaired.
    Validation results are preserved separately from final replay dispositions.
    """
    if not isinstance(recorded_response, (str, bytes)):
        raise TypeError("recorded_response must be exact text or bytes")
    inputs = deepcopy(dict(request_inputs))
    request = build_request(**inputs)
    parsed = parse_recorded_response(recorded_response, request=request)
    try:
        raw_bytes = recorded_response if isinstance(recorded_response, bytes) else recorded_response.encode("utf-8")
    except UnicodeEncodeError:
        # Preserve the original string in JSON; there is no valid UTF-8 digest.
        raw_bytes = None
    report: dict[str, Any] = {
        "schemaVersion": REPLAY_VERSION, "contractID": CONTRACT_ID, "artifactFamily": "hydroshare",
        "status": "processing_failed", "requestResult": deepcopy(request), "parseResult": deepcopy(parsed),
        "requestSha256": request.get("requestSha256"), "responseSha256": parsed.get("responseSha256"),
        "responseInputType": "bytes" if isinstance(recorded_response, bytes) else "text",
        "responseBytesHex": raw_bytes.hex() if parsed.get("responseSha256") is not None else None,
        "expectedRequestSha256": expected_request_sha256,
        "requestAssociation": "not_independently_attested" if expected_request_sha256 is None else "pending_digest_check",
        "validationResult": None, "validationPayload": None, "endpointMapping": None,
        "sourceSnapshot": None, "sourceCompleteness": None, "sourceDiagnostics": [],
        "finalRecords": [], "abstentionRecords": [], "diagnostics": [],
        "semanticStatus": "not_evaluated", "kgAuthorization": False, "graphAcceptance": False,
    }

    def seal() -> ReplayReport:
        """Bind all stage records and dispositions to a deterministic immutable digest."""
        snapshot = deepcopy(report)
        if isinstance(recorded_response, bytes):
            snapshot["parseResult"]["originalResponse"] = {"encoding": "hex", "value": recorded_response.hex()}
        canonical = json.dumps(snapshot, ensure_ascii=True, sort_keys=True, separators=(",", ":"), allow_nan=False)
        return ReplayReport(canonical, hashlib.sha256(canonical.encode("utf-8")).hexdigest(), raw_bytes)

    if request["status"] != "request_ready":
        report["diagnostics"].append({"reason": "request_construction_failed", "disposition": "processing_failed"})
        report["sourceDiagnostics"] = deepcopy(request.get("diagnostics", []))
        return seal()
    body = request["request"]
    report["sourceSnapshot"] = {k: deepcopy(body[k]) for k in (
        "owner", "sourceUnits", "selectedSourceUnitIDs", "authorityMetadata", "trustedProvenance",
        "acceptedSectionMapping") if k in body}
    report["sourceCompleteness"] = deepcopy(body["sourceCompleteness"])
    report["sourceDiagnostics"] = deepcopy(body["sourceDiagnostics"])
    if expected_request_sha256 is not None:
        if expected_request_sha256 != request["requestSha256"]:
            report["requestAssociation"] = "digest_mismatch"
            report["diagnostics"].append({"reason": "recorded_request_digest_mismatch", "disposition": "processing_failed"})
            return seal()
        report["requestAssociation"] = "matched_caller_supplied_digest"
    if parsed["status"] != "response_parsed":
        report["diagnostics"].extend(deepcopy(parsed["diagnostics"]))
        return seal()
    selected = set(body["selectedSourceUnitIDs"])
    rejected: dict[str, dict] = {}
    for record in parsed["candidateRecords"]:
        evidence = record["originalCandidate"].get("evidence")
        outside = [deepcopy(f.get("sourceUnitID")) for f in evidence if isinstance(f, Mapping)
                   and (not isinstance(f.get("sourceUnitID"), str) or f["sourceUnitID"] not in selected)] if isinstance(evidence, list) else []
        if record["parseDisposition"] != "pending_validation" or outside:
            rejected[record["candidateID"]] = {"parseDiagnostics": deepcopy(record["diagnostics"]),
                                             "unselectedSourceUnitIDs": outside}
    payload = {k: [deepcopy(row) for row in parsed["candidatePayload"][k] if row["candidateID"] not in rejected]
               for k in ("candidateNodes", "candidateEdges")}
    report["validationPayload"] = deepcopy(payload)
    report["validationScope"] = {"selectedSourceUnitIDs": deepcopy(body["selectedSourceUnitIDs"]),
        "quarantinedCandidateIDs": list(rejected), "sourceProjection": "selected_units_only",
        "completenessPolicy": "Request records full supplied-source coverage; validator completeness describes its restricted view."}
    abstracts = [r["unit"] for r in inputs["abstract_results"] if r.get("status") == "source_read_success"
                 and r["unit"].source_unit_id in selected]
    readmes = []
    for reader in inputs["readme_results"]:
        projected = deepcopy(reader)
        if isinstance(projected.get("sourceUnits"), list):
            projected["sourceUnits"] = [u for u in projected["sourceUnits"] if u.get("sourceUnitID") in selected]
        readmes.append(projected)
    report["endpointMapping"] = {"callerAcceptedEndpoints": deepcopy(inputs.get("accepted_endpoints") or []),
        "validatorAcceptedEndpoints": deepcopy(body["acceptedEndpoints"]),
        "validatorAuthorizedStubs": deepcopy(body["authorizedStubs"]),
        "acceptedAssertions": deepcopy(body["acceptedAssertions"])}
    validation = validate_dataset_candidates(payload, accepted_owner_id=inputs["accepted_owner_id"],
        trusted_provenance=inputs["trusted_provenance"], abstract_units=abstracts, readme_results=readmes,
        accepted_endpoints=body["acceptedEndpoints"], authorized_stubs=body["authorizedStubs"],
        accepted_assertions=body["acceptedAssertions"])
    report["validationResult"] = deepcopy(validation)
    checks = {r["candidateID"]: r for r in validation.get("candidateChecks", [])}
    for record in parsed["candidateRecords"]:
        cid = record["candidateID"]
        checked = checks.get(cid)
        final = {"candidateID": cid, "kind": record["kind"], "originalCandidate": deepcopy(record["originalCandidate"]),
            "parseDisposition": record["parseDisposition"], "parseDiagnostics": deepcopy(record["diagnostics"]),
            "validationRecord": deepcopy(checked), "validationDisposition": checked.get("disposition") if checked else None,
            "semanticStatus": "not_evaluated", "kgAuthorization": False}
        if cid in rejected:
            final.update(finalDisposition="rejected_invalid_assertion", replayDiagnostics=[
                {"reason": "parse_or_selected_unit_boundary_failure", **deepcopy(rejected[cid])}])
        elif checked is not None:
            final.update(finalDisposition=checked["disposition"], replayDiagnostics=[])
        else:
            final.update(finalDisposition="processing_failed", replayDiagnostics=[{"reason": "validator_did_not_return_candidate"}])
        report["finalRecords"].append(final)
    for record in parsed["abstentionRecords"]:
        report["abstentionRecords"].append({**deepcopy(record), "finalDisposition":
            "rejected_invalid_assertion" if record["parseDisposition"] == "local_abstention_error"
            else "recorded_claim_pending_validation"})
    report["status"] = "replay_completed" if validation["status"] == "candidate_checks_completed" else "processing_failed"
    if report["status"] == "processing_failed":
        report["diagnostics"].extend(deepcopy(validation.get("diagnostics", [])))
    return seal()
