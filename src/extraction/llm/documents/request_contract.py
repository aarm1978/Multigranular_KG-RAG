"""Offline ciroh_hub request and recorded-response boundary; Step 11 v0.3.

Implementation projection only. No candidate validation, provider, corpus reader,
response repair, semantic acceptance or graph authorization occurs here.
"""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from typing import Any, Mapping

from src.extraction.llm.semantic_target_profiles import CONTRACT_ID, get_profile

REQUEST_VERSION = "ciroh_hub-request/1.0.0"
RESPONSE_VERSION = "ciroh_hub-response/1.0.0"
FAMILY = "ciroh_hub"

WAVE_B_REQUEST_VERSION = 'ciroh_hub-request/1.1.0'
WAVE_B_PROMPT_IDENTIFIER = 'ciroh-hub-wave-b-clarification/0.1.0'
# Approved prospective wording; never alter legacy instruction bytes.
WAVE_B_INSTRUCTIONS = ('Distinguish a substantive scientific/data-processing Workflow from access, navigation, '
 'installation or launch instructions. Such instructions may support a coherent task-directed '
 'Procedure without also supporting a Workflow. Do not duplicate a Procedure as a Workflow solely '
 'because it has multiple steps. A processing sequence can be described without evidence of '
 'execution or success.',
 'A Step needs an identified instructional action in its Procedure. An automatic consequence or '
 'resulting state is not by itself a separately instructed action. Do not invent a check, '
 'confirmation or command to turn that outcome into a Step. Use the stated action and sequence '
 'context, preserving incomplete instructions when hidden, dynamic or unselected content leaves a '
 'gap.',
 'When selected prose independently supports a Procedure/Step and a procedural Parameter or '
 'identifiable displayed Example, you may propose the parent, dependent and required attachment '
 'edges together as candidates. Supply separate evidence for each assertion and valid ordered '
 'parentPath references from this page through hasProcedure, optionally hasStep, to the '
 "dependent's own attachment. Use the response contract's candidate_edge or trusted "
 'accepted_assertion references. These proposed paths are not accepted parents and do not satisfy '
 'semantic gates. If a parent or required relation is invalid or unresolved, its actual dependents '
 'remain held; independent candidates may survive. Do not invent a parent merely to enable '
 'Parameter or Example extraction.',
 'Parameter identity and procedural role require explanatory prose, including quoted wording/value '
 'when stated; a code key or argument alone is insufficient. Do not convert example values into '
 'defaults. A displayed fence may support only a literal possible Example with independently '
 'supported procedural attachment; never infer its execution, code semantics or parameters. No '
 'free-floating Parameters/Examples or nonempty output requirement is introduced. Parent semantic '
 'acceptance and all required relation/evidence gates remain pending until an independently '
 'authorized validation stage resolves them; never output attestations.')


WAVE_C_REQUEST_VERSION = 'ciroh_hub-request/1.2.0'
WAVE_C_PROMPT_IDENTIFIER = 'ciroh-hub-wave-c-step-tool-clarification/0.1.0'
# Final prospective clarification; the qualitative challenge cannot drive tuning.
WAVE_C_INSTRUCTIONS = ('A Step must represent a supported instructional action within a coherent Procedure. Lists of '
 'available capabilities, possible operations or automatic consequences do not by themselves '
 'constitute a sequence of instructed Steps. Narrative instructions are admissible; do not require '
 'imperative wording or numbered lists.',
 'Do not classify a data warehouse, storage system, infrastructure layer or generic services stack '
 'as Tool merely because it appears in a component hierarchy. Require independent evidence of an '
 'identifiable software Tool. Preserve valid hasComponent relations only when their endpoints are '
 'adequately typed. Do not invent alternative classes or activate excluded DataService targets.',
 'Preserve parent-dependent Example extraction, exact parentPath requirements and prose-grounded '
 'Parameter rules. Never promote proposed parent relationships to semantic acceptance.')

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
        "parentPathReferenceTypes": ["candidate_edge", "accepted_assertion"],
        "parentPathRule": "Step/Example/Parameter node paths run from this page through hasProcedure, optionally hasStep, and end with their own attachment. Edges to accepted dependent endpoints supply ancestry to the source parent. No path establishes semantic acceptance.",
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
    if request_version == WAVE_C_REQUEST_VERSION:
        body.update(schemaVersion=request_version, promptIdentifier=WAVE_C_PROMPT_IDENTIFIER,
                    instructions=deepcopy(INSTRUCTIONS) + list(WAVE_B_INSTRUCTIONS) + list(WAVE_C_INSTRUCTIONS))
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
        if (not isinstance(body, Mapping) or body.get("schemaVersion") not in (REQUEST_VERSION, WAVE_B_REQUEST_VERSION, WAVE_C_REQUEST_VERSION)
                or body.get("artifactFamily") != FAMILY
                or hashlib.sha256(_json(body).encode()).hexdigest() != request.get("requestSha256")):
            return fail("trusted_request_contract_or_hash_mismatch")
    except (TypeError, ValueError, RecursionError):
        return fail("trusted_request_malformed")
    version = body["schemaVersion"]
    expected_prompt = {REQUEST_VERSION: None, WAVE_B_REQUEST_VERSION: WAVE_B_PROMPT_IDENTIFIER,
                       WAVE_C_REQUEST_VERSION: WAVE_C_PROMPT_IDENTIFIER}[version]
    instructions = INSTRUCTIONS + (list(WAVE_B_INSTRUCTIONS) if version != REQUEST_VERSION else [])
    if version == WAVE_C_REQUEST_VERSION:
        instructions += list(WAVE_C_INSTRUCTIONS)
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

SPECIAL_FIELDS = {'node:A-DC06': ['parentPath'],
 'node:A-DC08': ['parentPath'],
 'node:A-DOM12': ['parentPath'],
 'edge:C-DC10': ['parentPath'],
 'edge:C-DC12': ['parentPath'],
 'edge:C-DC11': ['parentPath']}
REQUIRED_SPECIAL_FIELDS = {'node:A-DC06': ['parentPath'], 'node:A-DC08': ['parentPath'], 'node:A-DOM12': ['parentPath']}
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
 'Only original verified content_mdx is evidence authority. Selected static-visible '
 'prose/list/table/headings/literal components retain original Unicode offsets and verified Section '
 'bindings; never fabricate Section nodes or Docusaurus anchors.',
 'Comments, dynamic expressions, hidden/runtime/unmaterialized content are excluded; uncertain '
 'visibility stays held. Displayed fences are possible Example context only, never code semantics or '
 'Parameter identity.',
 'catalogs/C-DC17 and hasComponent/C-DC19 require explicit product/component hierarchy. '
 'describesTool/C-DC07, describesModel/C-DC16, describesDataset/C-DC27 and describesMethod/C-DC28 '
 'require substantive explanation; Method support stays pending. implementedBy/D-22 needs explicit '
 'implementation provenance.',
 'Procedure/hasProcedure requires coherent substantive instructions with a task/goal. Step/hasStep '
 'requires an action in its procedure with sequence/context. explainsWorkflow/C-DC09 requires a '
 'meaningful processing sequence, not one shell command.',
 'Example/hasExample and Parameter/hasParameter require accepted Procedure/Step parents and required '
 'hasProcedure/hasStep paths with independent evidence. Preserve explicit ordered parentPath '
 'references; structurally linked paths never attest parent acceptance. No free-floating discovery.',
 'Parameter identity/role requires explanatory prose with quoted wording/value when stated; no inferred '
 'defaults or configuration-key mining. No cross-page workflow assembly or DOI/citation enrichment.']


def build_request(page: Mapping[str, Any], reader_result: Mapping[str, Any], *, accepted_page_id: str,
                  selected_unit_ids: list[str], input_complete: bool,
                  accepted_section_mapping: Mapping[str, Any] | None = None,
                  accepted_endpoints: list[Mapping[str, Any]] | None = None,
                  accepted_assertions: list[Mapping[str, Any]] | None = None,
                  request_version: str = REQUEST_VERSION) -> dict[str, Any]:
    """Snapshot verified static MDX units, with fences only as Example context.

    Page replay and pure binders verify exact authority identity, original slices,
    hashes and optional accepted Section bindings. Only selected unit text enters
    request context; full MDX and hidden content are never expanded into a prompt.
    Source diagnostics/completeness remain separate from candidate outcomes.
    """
    if not isinstance(request_version, str) or request_version not in (REQUEST_VERSION, WAVE_B_REQUEST_VERSION, WAVE_C_REQUEST_VERSION):
        return {"status": "request_failed", "diagnostics": [{"reason": "unsupported_request_version"}]}
    from src.extraction.llm.documents.source_units import read_page_source_units
    from src.extraction.llm.documents.evidence_binding import bind_hub_evidence
    from src.extraction.llm.documents.example_context_binding import bind_example_context

    def fail(reason: str, diagnostics: list | None = None) -> dict:
        """Fail on selected unit integrity/visibility without semantic absence."""
        return {"status": "request_failed", "diagnostics": deepcopy(diagnostics or []) + [{"reason": reason}]}

    if (not isinstance(page, Mapping) or not isinstance(reader_result, Mapping)
            or not _selection(selected_unit_ids) or type(input_complete) is not bool
            or any(not isinstance(reader_result.get(k), list) for k in ("sourceUnits", "diagnostics"))):
        return fail("trusted_source_or_selection_malformed")
    replay = read_page_source_units(page, accepted_section_mapping=accepted_section_mapping)
    if replay["status"] != "source_read_success":
        return fail("authority_verification_failed", replay["diagnostics"])
    units = []
    for uid in selected_unit_ids:
        matches = [u for u in reader_result["sourceUnits"] if isinstance(u, Mapping) and u.get("sourceUnitID") == uid]
        if len(matches) != 1:
            return fail("selected_unit_missing_or_ambiguous")
        unit = matches[0]
        binder = bind_example_context if unit.get("contentKind") == "fenced_snippet" else bind_hub_evidence
        verified = next((u for u in replay["sourceUnits"] if u["sourceUnitID"] == uid), None)
        scoped_diagnostics = []
        for diagnostic in reader_result["diagnostics"]:
            unrelated = False
            if verified and isinstance(diagnostic, Mapping) and diagnostic.get("status") == "failed_source_or_evidence_binding":
                ref = diagnostic.get("sourceUnitID")
                first = diagnostic.get("startLine", diagnostic.get("sourceLine"))
                last = diagnostic.get("endLine", first)
                disjoint = type(first) is int and type(last) is int and 1 <= first <= last and (
                    last < verified["startLine"] or first > verified["endLine"])
                unrelated = (ref is not None and ref != uid and first is None) or (disjoint and ref != uid)
            if not unrelated:
                scoped_diagnostics.append(diagnostic)
        bound = binder(page, {**reader_result, "diagnostics": scoped_diagnostics}, uid, [{"evidenceText": unit.get("text")}],
            accepted_page_id=accepted_page_id, accepted_section_mapping=accepted_section_mapping)
        if bound["status"] not in {"evidence_bound", "example_context_bound"}:
            return fail("selected_unit_not_verified_visible", bound["diagnostics"])
        units.append(deepcopy(unit))
    complete = (input_complete and not reader_result["diagnostics"] and not replay["diagnostics"]
                and reader_result["sourceUnits"] == replay["sourceUnits"])
    return _finish({"endpointID": accepted_page_id, "inventoryId": "A-DC01", "class": "DocumentationPage",
        "page_key": page["page_key"], "canonical_url": page["canonical_url"]}, units, selected_unit_ids,
        {"inputComplete": complete, "callerInputComplete": input_complete, "readerStatus": reader_result.get("status"),
         "reviewRequired": reader_result.get("reviewRequired")}, reader_result["diagnostics"],
        [] if accepted_endpoints is None else accepted_endpoints, [] if accepted_assertions is None else accepted_assertions,
        {"authorityMetadata": {k: deepcopy(v) for k, v in replay["authority"].items() if k != "text"},
         "acceptedSectionMapping": deepcopy(accepted_section_mapping)}, request_version=request_version)
