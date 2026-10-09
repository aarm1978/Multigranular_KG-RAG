"""Offline hydroshare request and recorded-response boundary; Step 11 v0.3.

Implementation projection only. No candidate validation, provider, corpus reader,
response repair, semantic acceptance or graph authorization occurs here.
"""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from typing import Any, Mapping

from src.extraction.llm.semantic_target_profiles import CONTRACT_ID, get_profile

REQUEST_VERSION = "hydroshare-request/1.0.0"
RESPONSE_VERSION = "hydroshare-response/1.0.0"
FAMILY = "hydroshare"


def _text(value: Any) -> bool:
    """Require nonempty exact strings without trimming caller content."""
    return isinstance(value, str) and bool(value.strip())


def _json(value: Any) -> str:
    """Serialize deterministic record bytes, without changing source strings."""
    return json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":"), allow_nan=False)


def _schema() -> dict[str, Any]:
    """Describe the strict envelope and source-specific candidate field boundary."""
    return {"schemaVersion": RESPONSE_VERSION,
        "envelopeFields": ["schemaVersion", "candidateNodes", "candidateEdges", "abstentions"],
        "nodeFields": ["candidateID", "inventoryId", "class", "label", "evidence", "endpoint"],
        "edgeFields": ["candidateID", "inventoryId", "relation", "source", "target", "evidence"],
        "requiredNodeFields": ["candidateID", "inventoryId", "class", "label", "evidence"],
        "requiredEdgeFields": ["candidateID", "inventoryId", "relation", "source", "target", "evidence"],
        "specialFields": deepcopy(SPECIAL_FIELDS), "requiredSpecialFields": deepcopy(REQUIRED_SPECIAL_FIELDS),
        "recordIdentity": "Unique nonempty candidateID/abstentionID; source-local proposal IDs, never canonical KG IDs.",
        "referenceFields": ["referenceType", "referenceID"], "referenceTypes": list(REFERENCE_TYPES),
        "evidenceFields": ["sourceUnitID", "evidenceText", "locatorAnchor", "contribution"],
        "multiFragmentRule": "Each fragment retains an explicit contribution; never concatenate or repair evidence.",
        "abstentionFields": ["abstentionID", "inventoryId", "sourceUnitIDs", "disposition", "reason"],
        "abstentionDispositions": ["abstained_no_evidence", "abstained_ambiguous_semantics"],
        "abstentionPolicy": "Recorded claim only, never an accepted outcome; no implicit abstention from empty output.",
        "forbiddenModelAuthority": "No provenance, coordinates, provider metadata, gate attestations or graph authorization."}


def _finish(owner: dict, units: list[dict], selection: list[str], completeness: dict,
            diagnostics: list, endpoints: Any, assertions: Any, extra: dict | None = None) -> dict:
    """Snapshot trusted request context; caller inventories are never model output."""
    profile = get_profile(FAMILY)
    if not isinstance(endpoints, list) or not isinstance(assertions, list):
        return {"status": "request_failed", "diagnostics": [{"reason": "trusted_inventory_malformed"}]}
    known = {owner["endpointID"]: owner}
    for row in endpoints:
        if not isinstance(row, Mapping) or not _text(row.get("endpointID")) or row["endpointID"] in known:
            return {"status": "request_failed", "diagnostics": [{"reason": "trusted_endpoint_identity_invalid"}]}
        policy = profile["entities"].get(row.get("inventoryId")) if _text(row.get("inventoryId")) else None
        if not policy or row.get("class") != policy["declaration"]["name"]:
            return {"status": "request_failed", "diagnostics": [{"reason": "trusted_endpoint_type_invalid"}]}
        known[row["endpointID"]] = row
    seen = set()
    for row in assertions:
        if not isinstance(row, Mapping) or any(not _text(row.get(k)) for k in
                ("assertionID", "inventoryId", "relation", "sourceID", "targetID")):
            return {"status": "request_failed", "diagnostics": [{"reason": "trusted_assertion_malformed"}]}
        if (row["assertionID"] in seen or row["sourceID"] not in known or row["targetID"] not in known
                or profile["relations"].get(row["inventoryId"], {}).get("declaration", {}).get("name") != row["relation"]):
            return {"status": "request_failed", "diagnostics": [{"reason": "trusted_assertion_inventory_invalid"}]}
        seen.add(row["assertionID"])
    body = {"schemaVersion": REQUEST_VERSION, "contractID": CONTRACT_ID, "artifactFamily": FAMILY,
        "targetProfile": profile, "owner": deepcopy(owner), "selectedSourceUnitIDs": deepcopy(selection),
        "contextSelection": "caller_ordered_exact_units; no concatenation, expansion or normalized evidence",
        "sourceUnits": deepcopy(units), "sourceCompleteness": deepcopy(completeness),
        "sourceDiagnostics": deepcopy(diagnostics), "acceptedEndpoints": deepcopy(endpoints),
        "acceptedAssertions": deepcopy(assertions), "instructions": deepcopy(INSTRUCTIONS), "responseContract": _schema(),
        "semanticStatus": "not_evaluated", "kgAuthorization": False, **deepcopy(extra or {})}
    try:
        digest = hashlib.sha256(_json(body).encode("utf-8")).hexdigest()
    except (TypeError, ValueError, RecursionError):
        return {"status": "request_failed", "diagnostics": [{"reason": "non_json_trusted_context"}]}
    return {"status": "request_ready", "request": body, "requestSha256": digest, "diagnostics": []}


def _selection(value: Any) -> bool:
    """Require explicit, nonempty, uniquely identified caller context."""
    return isinstance(value, list) and bool(value) and all(_text(v) for v in value) and len(set(value)) == len(value)


def parse_recorded_response(raw: bytes | str, *, request: Mapping[str, Any]) -> dict[str, Any]:
    """Parse exact recorded JSON; preserve local errors for downstream validation.

    request is the caller-owned build_request result. No model field is promoted
    to trusted metadata. candidatePayload retains even invalid identifiable rows
    unchanged: candidateRecords mark their parse errors for Package 3B. This is
    syntax/boundary checking only, not endpoint, evidence or semantic validation.
    UTF-8 bytes are hashed before decoding; string inputs are hashed as exact UTF-8.
    Duplicate JSON keys, nonfinite numbers and duplicate/unidentifiable record IDs
    are globally unprocessable. Markdown fences and trailing prose are not repaired.
    """
    result: dict[str, Any] = {"status": "processing_failed", "originalResponse": raw,
        "artifactFamily": FAMILY, "contractID": CONTRACT_ID,
        "requestContractVersion": REQUEST_VERSION, "responseContractVersion": RESPONSE_VERSION,
        "responseSha256": None, "candidatePayload": None, "candidateRecords": [], "abstentionRecords": [],
        "diagnostics": [], "semanticStatus": "not_evaluated", "kgAuthorization": False}

    def fail(reason: str) -> dict:
        """Fail globally without generating a no-evidence outcome."""
        result["diagnostics"].append({"reason": reason, "disposition": "processing_failed"})
        return result

    if not isinstance(raw, (str, bytes)):
        return fail("response_not_text_or_bytes")
    try:
        encoded = raw if isinstance(raw, bytes) else raw.encode("utf-8")
        result["responseSha256"] = hashlib.sha256(encoded).hexdigest()
        decoded = encoded.decode("utf-8")
        result["responseText"] = decoded
    except UnicodeError:
        return fail("response_invalid_utf8")
    if not isinstance(request, Mapping) or request.get("status") != "request_ready":
        return fail("trusted_request_not_ready")
    body = request.get("request")
    try:
        if (not isinstance(body, Mapping) or body.get("schemaVersion") != REQUEST_VERSION
                or body.get("artifactFamily") != FAMILY
                or hashlib.sha256(_json(body).encode()).hexdigest() != request.get("requestSha256")):
            return fail("trusted_request_contract_or_hash_mismatch")
    except (TypeError, ValueError, RecursionError):
        return fail("trusted_request_malformed")
    result["requestSha256"] = request["requestSha256"]

    def pairs(items: list) -> dict:
        """Reject duplicate object keys instead of silently selecting one value."""
        obj = {}
        for key, value in items:
            if key in obj:
                raise ValueError("duplicate key")
            obj[key] = value
        return obj

    def invalid_number(value: str) -> None:
        """Reject JSON extensions such as NaN and Infinity."""
        raise ValueError(value)

    try:
        parsed = json.loads(decoded, object_pairs_hook=pairs, parse_constant=invalid_number)
        _json(parsed)  # Reject overflowed JSON floating-point values too.
    except (ValueError, TypeError, RecursionError):
        return fail("response_invalid_json")
    try:
        result["originalParsedResponse"] = deepcopy(parsed)
    except RecursionError:
        return fail("response_nesting_unprocessable")
    if (not isinstance(parsed, dict) or set(parsed) != set(_schema()["envelopeFields"])
            or parsed.get("schemaVersion") != RESPONSE_VERSION
            or any(not isinstance(parsed.get(k), list) for k in ("candidateNodes", "candidateEdges", "abstentions"))):
        return fail("response_envelope_invalid")
    identifiers = []
    for group, key in (("candidateNodes", "candidateID"), ("candidateEdges", "candidateID"), ("abstentions", "abstentionID")):
        for row in parsed[group]:
            if not isinstance(row, dict) or not _text(row.get(key)):
                return fail("response_record_unidentifiable")
            identifiers.append(row[key])
    if len(set(identifiers)) != len(identifiers):
        return fail("response_record_identity_ambiguous")
    selection = body["selectedSourceUnitIDs"]
    schema = _schema()
    for kind, group in (("node", "candidateNodes"), ("edge", "candidateEdges")):
        for row in parsed[group]:
            errors = []
            fields = set(schema["nodeFields" if kind == "node" else "edgeFields"])
            required = fields - {"endpoint"}
            identifier = row.get("inventoryId")
            special = SPECIAL_FIELDS.get(kind + ":" + identifier, []) if isinstance(identifier, str) else []
            fields.update(special)
            required.update(REQUIRED_SPECIAL_FIELDS.get(kind + ":" + identifier, []) if isinstance(identifier, str) else [])
            if set(row) - fields or required - set(row):
                errors.append("candidate_fields_invalid")
            if any(not _text(row.get(k)) for k in ("inventoryId", "class", "label") if kind == "node") or (
                    kind == "edge" and any(not _text(row.get(k)) for k in ("inventoryId", "relation"))):
                errors.append("candidate_scalar_fields_invalid")
            for key in ("endpoint",) if kind == "node" else ("source", "target"):
                if key not in row:
                    continue
                ref = row[key]
                if not isinstance(ref, dict) or set(ref) != {"referenceType", "referenceID"} or not _text(ref.get("referenceID")) or ref.get("referenceType") not in REFERENCE_TYPES:
                    errors.append("endpoint_reference_invalid")
            if "parentPath" in row:
                path = row["parentPath"]
                if not isinstance(path, list) or any(not isinstance(r, dict) or set(r) != {"referenceType", "referenceID"}
                        or not _text(r.get("referenceID")) or r.get("referenceType") not in ("candidate_edge", "accepted_assertion") for r in path):
                    errors.append("parent_path_fields_invalid")
            for key in special:
                if key != "parentPath" and key in row and not _text(row[key]):
                    errors.append("special_field_invalid")
            evidence = row.get("evidence")
            if not isinstance(evidence, list) or not evidence:
                errors.append("evidence_missing_or_malformed")
            else:
                for fragment in evidence:
                    if (not isinstance(fragment, dict) or set(fragment) - set(schema["evidenceFields"])
                            or not _text(fragment.get("sourceUnitID")) or not _text(fragment.get("evidenceText"))
                            or fragment.get("sourceUnitID") not in selection
                            or "locatorAnchor" in fragment and not _text(fragment["locatorAnchor"])
                            or (len(evidence) > 1 or "contribution" in fragment) and not _text(fragment.get("contribution"))):
                        errors.append("evidence_fields_invalid")
            result["candidateRecords"].append({"kind": kind, "candidateID": row["candidateID"],
                "originalCandidate": deepcopy(row), "parseDisposition": "local_candidate_error" if errors else "pending_validation",
                "diagnostics": errors, "eligibleForLocalizedValidation": True})
    for row in parsed["abstentions"]:
        errors = []
        if (set(row) != set(schema["abstentionFields"]) or not _text(row.get("reason"))
                or not _text(row.get("inventoryId")) or row.get("disposition") not in schema["abstentionDispositions"]
                or not isinstance(row.get("sourceUnitIDs"), list) or not row["sourceUnitIDs"]
                or any(not _text(u) or u not in selection for u in row["sourceUnitIDs"])):
            errors.append("abstention_fields_invalid")
        target = row.get("inventoryId")
        if isinstance(target, str) and target not in body["targetProfile"]["entities"] and target not in body["targetProfile"]["relations"]:
            errors.append("abstention_target_not_in_profile")
        if row.get("disposition") == "abstained_no_evidence" and body["sourceCompleteness"]["inputComplete"] is not True:
            errors.append("no_evidence_precondition_unverified")
        result["abstentionRecords"].append({"originalAbstention": deepcopy(row),
            "parseDisposition": "local_abstention_error" if errors else "recorded_claim_pending_validation",
            "diagnostics": errors, "semanticStatus": "not_evaluated", "kgAuthorization": False})
    result["candidatePayload"] = {k: deepcopy(parsed[k]) for k in ("candidateNodes", "candidateEdges")}
    result["status"] = "response_parsed"
    return result

SPECIAL_FIELDS = {}
REQUIRED_SPECIAL_FIELDS = {}
REFERENCE_TYPES = ['accepted_endpoint', 'authorized_stub', 'candidate_node']
INSTRUCTIONS = ['Use only frozen profile inventory IDs, declaration names and signatures. Predict concrete model '
 'subtypes only. DataService/servesDataset are inactive; D-26 and superclass/superproperty assertions '
 'are pipeline-derived, not model-authorable.',
 'Every model-authored node and every edge needs independently supplied literal evidenceText and '
 'sourceUnitID. Co-occurrence/URLs never prove a stronger role; preserve conflicting claims, quotation '
 'bytes and each fragment contribution.',
 'New occurrences are source-local; reuse only exact supplied endpoints. Accepted equivalent assertions '
 'must not be materialized again; preserve their supporting citations. Never merge by name or repair '
 'external identities.',
 'Return only the versioned JSON envelope. Use explicit abstention records only as claims about '
 'selected targets/units; never infer no evidence from failed/incomplete source reads or empty output. '
 'Structural/literal success is not semantic acceptance; no gate attestations or KG authorization.',
 'Use only selected verified abstract/README units from this resource; no dataset-file inspection, '
 'README acquisition or enrichment.',
 'Variable/C-D16 requires explicit measurable resource contents, not a topic mention. Measurement/C-D17 '
 'requires README-only individuating observation evidence (observable/value/unit or observation '
 'identifier/conditions); a variable list is insufficient and zero yield is allowed.',
 'Distinguish Tool usesTool/C-D18 from mentionsTool/C-D24, and concrete model usesModel/C-D25 from '
 'mentionsModel/C-D26; links and co-occurrence do not prove use. C-D26 is not pipeline D-26.',
 'Workflow/C-D22 requires a substantive scientific processing sequence. generatedBy/D-17 needs explicit '
 'generation provenance and an exact Repository endpoint or caller-authorized source-scoped stub; never '
 'invent IDs.']


def build_request(*, accepted_owner_id: str, trusted_provenance: Mapping[str, Any],
                  selected_unit_ids: list[str], abstract_results: list[Mapping[str, Any]],
                  readme_results: list[Mapping[str, Any]], input_complete: bool,
                  accepted_endpoints: list[Mapping[str, Any]] | None = None,
                  authorized_stubs: list[Mapping[str, Any]] | None = None,
                  accepted_assertions: list[Mapping[str, Any]] | None = None) -> dict[str, Any]:
    """Build from caller-owned abstract/README read results, without acquisition.

    input_complete attests supplied source coverage, not semantic completeness.
    Optional absence is retained without being treated as a technical failure.
    Selecting a failed/missing unit fails the request; unselected source failures
    remain diagnostics and make the request incomplete. Selection order is exact.
    A computed-only digest remains computed-only; no acquisition claim is added.
    """
    from src.extraction.llm.datasets.source_units import AbstractSourceUnit, build_abstract_source_unit, bind_readme_evidence

    diagnostics, reads, sources = [], [], {}

    def fail(reason: str) -> dict:
        """Preserve source failures without manufacturing semantic abstentions."""
        return {"status": "request_failed", "diagnostics": deepcopy(diagnostics) + [{"reason": reason}]}

    if (not _text(accepted_owner_id) or not isinstance(trusted_provenance, Mapping)
            or not _text(trusted_provenance.get("snapshotID"))
            or trusted_provenance.get("sourceVersion") is not None and not _text(trusted_provenance["sourceVersion"])
            or type(input_complete) is not bool or not _selection(selected_unit_ids)
            or not isinstance(abstract_results, list) or not isinstance(readme_results, list)):
        return fail("trusted_source_or_selection_malformed")
    complete = input_complete
    for kind, results in (("abstract", abstract_results), ("README", readme_results)):
        for reader in results:
            if not isinstance(reader, Mapping):
                return fail("source_result_malformed")
            status = reader.get("status")
            reads.append({"sourceField": kind, "status": status, "inputComplete": reader.get("inputComplete")})
            if not isinstance(reader.get("diagnostics", []), list):
                return fail("source_diagnostics_malformed")
            diagnostics.extend(deepcopy(reader.get("diagnostics", [])))
            if "diagnostic" in reader:
                diagnostics.append(deepcopy(reader["diagnostic"]))
            if status == "optional_input_absent":
                continue
            if status != "source_read_success" or reader.get("inputComplete") is not True:
                complete = False
            if status != "source_read_success":
                continue
            if kind == "abstract":
                unit = reader.get("unit")
                if not isinstance(unit, AbstractSourceUnit):
                    return fail("abstract_unit_malformed")
                replay = build_abstract_source_unit({"resource_id": unit.resource_id, "abstract": unit.text},
                    accepted_owner_id=accepted_owner_id, provenance=trusted_provenance,
                    expected_authority_text_sha256=unit.expected_authority_text_sha256)
                valid = replay.get("unit") == unit
                if not valid:
                    complete = False
                    diagnostics.append({"reason": "abstract_integrity_or_provenance_mismatch", "sourceUnitID": unit.source_unit_id})
                sources.setdefault(unit.source_unit_id, []).append((unit.to_record(), valid, reader))
            else:
                if not isinstance(reader.get("sourceUnits"), list):
                    return fail("readme_units_malformed")
                for unit in reader["sourceUnits"]:
                    if not isinstance(unit, Mapping) or not _text(unit.get("sourceUnitID")):
                        return fail("readme_unit_unidentifiable")
                    valid = (unit.get("resource_id") == accepted_owner_id
                             and unit.get("snapshotID") == trusted_provenance["snapshotID"]
                             and unit.get("sourceVersion") == trusted_provenance.get("sourceVersion"))
                    if not valid:
                        complete = False
                        diagnostics.append({"reason": "readme_owner_or_snapshot_mismatch", "sourceUnitID": unit["sourceUnitID"]})
                    sources.setdefault(unit["sourceUnitID"], []).append((unit, valid, reader))
    units = []
    for uid in selected_unit_ids:
        matches = sources.get(uid, [])
        if len(matches) != 1 or not matches[0][1]:
            return fail("selected_unit_missing_ambiguous_or_provenance_mismatch")
        unit, _, reader = matches[0]
        if unit["sourceField"] == "README":
            bound = bind_readme_evidence(reader, uid, [{"evidenceText": unit.get("text")}])
            if bound["status"] != "evidence_bound":
                diagnostics.extend(bound["diagnostics"])
                return fail("selected_readme_verification_failed")
        units.append(deepcopy(unit))
    stubs = [] if authorized_stubs is None else authorized_stubs
    if not isinstance(stubs, list):
        return fail("authorized_stub_inventory_malformed")
    for stub in stubs:
        if (not isinstance(stub, Mapping) or stub.get("inventoryId") != "A-C01" or stub.get("class") != "Repository"
                or stub.get("resource_id") != accepted_owner_id or stub.get("snapshotID") != trusted_provenance["snapshotID"]
                or stub.get("sourceVersion") != trusted_provenance.get("sourceVersion") or not _text(stub.get("authorizationID"))):
            return fail("authorized_stub_provenance_mismatch")
    if accepted_endpoints is not None and not isinstance(accepted_endpoints, list):
        return fail("trusted_endpoint_inventory_malformed")
    return _finish({"endpointID": accepted_owner_id, "resource_id": accepted_owner_id, "inventoryId": "A-D01",
        "class": "DatasetResource", "snapshotID": trusted_provenance["snapshotID"],
        "sourceVersion": trusted_provenance.get("sourceVersion")}, units, selected_unit_ids,
        {"inputComplete": complete, "callerInputComplete": input_complete, "reads": reads,
         "meaning": "source coverage only; optional absence is not abstention"}, diagnostics,
        ([] if accepted_endpoints is None else accepted_endpoints) + stubs,
        [] if accepted_assertions is None else accepted_assertions,
        {"authorizedStubs": deepcopy(stubs), "acceptedEndpoints": deepcopy(accepted_endpoints or []),
         "trustedProvenance": deepcopy(dict(trusted_provenance))})
