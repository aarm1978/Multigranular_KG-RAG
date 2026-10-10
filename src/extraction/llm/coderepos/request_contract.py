"""Offline github request and recorded-response boundary; Step 11 v0.3.

Implementation projection only. No candidate validation, provider, corpus reader,
response repair, semantic acceptance or graph authorization occurs here.
"""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from typing import Any, Mapping

from src.extraction.llm.semantic_target_profiles import CONTRACT_ID, get_profile

REQUEST_VERSION = "github-request/1.0.0"
RESPONSE_VERSION = "github-response/1.0.0"
FAMILY = "github"

WAVE_B_REQUEST_VERSION = 'github-request/1.1.0'
WAVE_B_PROMPT_IDENTIFIER = 'github-wave-b-clarification/0.1.0'
# Approved prospective wording; never alter legacy instruction bytes.
WAVE_B_INSTRUCTIONS = ('A Function candidate must identify a named programming function or object-oriented method '
 'explicitly described in eligible prose, including its stated computational role. A scientific '
 'Method is not a software Function. Do not turn a repository goal, notebook task, API as a whole, '
 'or broad capability into a Function by inventing an action label. A mathematical function name '
 'alone does not establish software Function identity; use the prose context without examining '
 'code or inferring signatures. Preserve ambiguity when identity or granularity is unclear.',
 'Distinguish a named, prose-characterized Algorithm from a formula, distribution, model, broad '
 'method or Workflow. A formula or technique mention alone does not establish every one of those '
 'classes. A StatisticalModel needs its own named model identity under the frozen profile. A '
 'Workflow requires a substantive processing sequence. Do not create a GitHub-local Publication '
 'Method or use Algorithm as a fallback for an unsupported Method. Preserve conflicting subtype '
 'evidence rather than resolving it through names or background knowledge.',
 'Evaluate each hasPurpose category independently against the exact six frozen definitions and the '
 "repository's own purpose. An external product's purpose, incidental example, dependency or "
 'keyword does not establish repository membership. scientific_experimentation requires that '
 "supporting simulations, experiments, calibration or evaluation is central to the repository's "
 'purpose; it does not require proof that the repository executed experiments. Multiple categories '
 'need independent support for each assignment; one sufficiently explicit passage may support more '
 'than one. Reuse the exact controlled seed endpoints, never create new category nodes, and retain '
 'unclassified/ambiguous outcomes outside the KG.',
 "Consider the repository's own identifiable software product when prose supports it; do not "
 'replace that identity with generic capability Functions. Independently quote an implementedBy '
 'relation only when the prose establishes that this exact repository implements or provides the '
 'source for the valid Tool/model. Its direction is Tool/model to Repository. uses and mentions '
 'retain their separate evidence criteria; use, a dependency or a link alone is not '
 'implementation. Do not force an own-product node, merge by name, infer external endpoints, or '
 "turn dependency/upstream versions into the repository's ModelVersion. Preserve every existing "
 'ModelVersion and implementsMethod condition and unresolved outcome.')


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
        "purposeClassification": "C-C07 classification is proposed, unclassified or ambiguous. For the latter two, categoryKey and target are null and reason is required; they remain non-KG diagnostics.",
        "referenceFields": ["referenceType", "referenceID"], "referenceTypes": list(REFERENCE_TYPES),
        "evidenceFields": ["sourceUnitID", "evidenceText", "locatorAnchor", "contribution"],
        "multiFragmentRule": "Each fragment retains an explicit contribution; never concatenate or repair evidence.",
        "abstentionFields": ["abstentionID", "inventoryId", "sourceUnitIDs", "disposition", "reason"],
        "abstentionDispositions": ["abstained_no_evidence", "abstained_ambiguous_semantics"],
        "abstentionPolicy": "Recorded claim only, never an accepted outcome; no implicit abstention from empty output.",
        "forbiddenModelAuthority": "No provenance, coordinates, provider metadata, gate attestations or graph authorization."}


def _finish(owner: dict, units: list[dict], selection: list[str], completeness: dict,
            diagnostics: list, endpoints: Any, assertions: Any, extra: dict | None = None,
            request_version: str = REQUEST_VERSION) -> dict:
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
    if request_version == WAVE_B_REQUEST_VERSION:
        body.update(schemaVersion=request_version, promptIdentifier=WAVE_B_PROMPT_IDENTIFIER,
                    instructions=deepcopy(INSTRUCTIONS) + list(WAVE_B_INSTRUCTIONS))
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
        if (not isinstance(body, Mapping) or body.get("schemaVersion") not in (REQUEST_VERSION, WAVE_B_REQUEST_VERSION)
                or body.get("artifactFamily") != FAMILY
                or hashlib.sha256(_json(body).encode()).hexdigest() != request.get("requestSha256")):
            return fail("trusted_request_contract_or_hash_mismatch")
    except (TypeError, ValueError, RecursionError):
        return fail("trusted_request_malformed")
    version = body["schemaVersion"]
    expected_prompt = WAVE_B_PROMPT_IDENTIFIER if version == WAVE_B_REQUEST_VERSION else None
    instructions = INSTRUCTIONS + (list(WAVE_B_INSTRUCTIONS) if version == WAVE_B_REQUEST_VERSION else [])
    if body.get("promptIdentifier") != expected_prompt or body.get("instructions") != instructions:
        return fail("trusted_request_prompt_variant_mismatch")
    result["requestContractVersion"] = version
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
                if (kind == "edge" and identifier == "C-C07" and key == "target" and ref is None
                        and row.get("classification") in ("unclassified", "ambiguous")):
                    continue
                if not isinstance(ref, dict) or set(ref) != {"referenceType", "referenceID"} or not _text(ref.get("referenceID")) or ref.get("referenceType") not in REFERENCE_TYPES:
                    errors.append("endpoint_reference_invalid")
            if "parentPath" in row:
                path = row["parentPath"]
                if not isinstance(path, list) or any(not isinstance(r, dict) or set(r) != {"referenceType", "referenceID"}
                        or not _text(r.get("referenceID")) or r.get("referenceType") not in ("candidate_edge", "accepted_assertion") for r in path):
                    errors.append("parent_path_fields_invalid")
            for key in special:
                if key == "categoryKey" and row.get("classification") in ("unclassified", "ambiguous") and row.get(key) is None:
                    continue
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

SPECIAL_FIELDS = {'node:A-C10': ['productRepositoryID'],
 'edge:C-C07': ['categoryKey', 'classification', 'reason'],
 'edge:C-C16': ['methodSurfaceForm', 'candidatePublicationIdentifier']}
REQUIRED_SPECIAL_FIELDS = {'node:A-C10': ['productRepositoryID'], 'edge:C-C07': ['categoryKey']}
REFERENCE_TYPES = ['accepted_endpoint', 'candidate_node']
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
 'Use verified descriptive prose only: Phase A README precedence, distinct downloaded eligible prose '
 'and original notebook Markdown cells. No code/output/runtime interpretation, dependency manifests, '
 'topics, badges or administrative content. file_role alone does not establish eligibility.',
 'RepositoryPurpose nodes are the six controlled seeds, never model-created categories. Propose '
 'separate C-C07 edges with repository-specific purpose evidence; no other category. Unclassified or '
 'ambiguous purpose remains a non-KG diagnostic.',
 'Function/C-C08 and Algorithm/C-C20 must be identified and described in prose. Workflow/C-C10 requires '
 'a substantive processing sequence.',
 'Distinguish usesTool/C-C11, mentionsTool/C-C22, usesModel/C-C21, mentionsModel/C-C23 and '
 'implementedBy/D-22; use is not implementation. usesDataset/C-C15 needs an exact identifiable dataset '
 'endpoint, not a URL alone.',
 'ModelVersion/C-C09 concerns only the repository own software/model product, explicitly quoted in '
 'prose and absent from deterministic assertions; dependency/runtime/upstream versions do not qualify. '
 'productRepositoryID is a claim, not a gate attestation.',
 'implementsMethod/C-C16 requires explicit implementation and a valid traceable accepted Publication '
 'A-P13 occurrence. DOI/name matching cannot identify it. Preserve unresolved hints; no GitHub-local '
 'Method, automatic alignment or materialization. Later resolution requires separately approved Step 14 '
 'after Step 13 Publication production.']


def build_request(reader_result: Mapping[str, Any], *, accepted_repository: Mapping[str, Any],
                  selected_unit_ids: list[str], input_complete: bool,
                  accepted_endpoints: list[Mapping[str, Any]] | None = None,
                  accepted_assertions: list[Mapping[str, Any]] | None = None,
                  request_version: str = REQUEST_VERSION) -> dict[str, Any]:
    """Snapshot only selected verified README/prose/notebook-Markdown units.

    Uses the pure binder to verify each entire exact unit, never the file reader.
    input_complete is a caller coverage attestation, combined with reader failures;
    it never asserts semantic coverage. Preserve frozen commit, case-sensitive
    path, raw-file/cell authority hashes, selection order and all read diagnostics.
    """
    if not isinstance(request_version, str) or request_version not in (REQUEST_VERSION, WAVE_B_REQUEST_VERSION):
        return {"status": "request_failed", "diagnostics": [{"reason": "unsupported_request_version"}]}
    from src.extraction.llm.coderepos.evidence_binding import bind_repository_evidence
    from src.extraction.llm.coderepos.purpose_validation import purpose_vocabulary

    def fail(reason: str, diagnostics: list | None = None) -> dict:
        """Hold selected source failures without dropping them from context."""
        return {"status": "request_failed", "diagnostics": deepcopy(diagnostics or []) + [{"reason": reason}]}

    if (not isinstance(reader_result, Mapping) or not isinstance(accepted_repository, Mapping)
            or not _selection(selected_unit_ids) or type(input_complete) is not bool
            or any(not isinstance(reader_result.get(k), list) for k in ("sourceUnits", "authorities", "reads", "diagnostics"))):
        return fail("trusted_source_or_selection_malformed")
    units, authorities = [], []
    for uid in selected_unit_ids:
        matches = [u for u in reader_result["sourceUnits"] if isinstance(u, Mapping) and u.get("sourceUnitID") == uid]
        if len(matches) != 1:
            return fail("selected_unit_missing_or_ambiguous")
        unit = matches[0]
        bound = bind_repository_evidence(reader_result, uid, [{"evidenceText": unit.get("text")}], accepted_repository=accepted_repository)
        if bound["status"] != "evidence_bound":
            return fail("selected_unit_not_verified_eligible", bound["diagnostics"])
        units.append(deepcopy(unit))
        # Metadata only: do not expand selected context to the full file/cell.
        authority = next(a for a in reader_result["authorities"] if a.get("path") == unit["path"] and a.get("cellIndex") == unit["cellIndex"])
        metadata = {k: deepcopy(v) for k, v in authority.items() if k != "text"}
        if metadata not in authorities:
            authorities.append(metadata)
    if accepted_endpoints is not None and not isinstance(accepted_endpoints, list):
        return fail("trusted_endpoint_inventory_malformed")
    seeds = purpose_vocabulary()
    endpoints = deepcopy([] if accepted_endpoints is None else accepted_endpoints)
    seed_ids = {s["nodeID"] for s in seeds}
    if any(isinstance(e, Mapping) and e.get("inventoryId") == "A-C07" and (not _text(e.get("endpointID")) or e["endpointID"] not in seed_ids) for e in endpoints):
        return fail("unknown_controlled_purpose_endpoint")
    for seed in seeds:
        if not any(isinstance(e, Mapping) and e.get("endpointID") == seed["nodeID"] for e in endpoints):
            endpoints.append({"endpointID": seed["nodeID"], "inventoryId": "A-C07", "class": "RepositoryPurpose"})
    complete = (input_complete and reader_result.get("inputComplete") is True
                and not reader_result["diagnostics"])
    return _finish({**deepcopy(dict(accepted_repository)), "endpointID": accepted_repository["canonicalArtifactID"],
        "inventoryId": "A-C01", "class": "Repository"}, units, selected_unit_ids,
        {"inputComplete": complete, "callerInputComplete": input_complete,
         "readerInputComplete": reader_result.get("inputComplete"), "reads": deepcopy(reader_result["reads"])},
        reader_result["diagnostics"], endpoints, [] if accepted_assertions is None else accepted_assertions,
        {"authorityMetadata": authorities, "purposeVocabulary": seeds}, request_version=request_version)
