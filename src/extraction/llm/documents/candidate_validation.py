"""Hub source-local structural and literal candidate checks, Step 11 v0.3.

No procedural meaning, semantic acceptance or KG authorization is established.
Only the frozen ontology specification is read; page inputs remain in memory.
"""

from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from typing import Any, Mapping

from src.extraction.llm.documents.source_units import read_page_source_units
from src.extraction.llm.documents.evidence_binding import bind_hub_evidence
from src.extraction.llm.semantic_target_profiles import CONTRACT_ID, get_profile, check_target


def validate_procedure_candidate(
    page: Mapping[str, Any], reader_result: Mapping[str, Any], payload: Mapping[str, Any], *,
    accepted_page_id: str, accepted_section_mapping: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Check one node/edge proposal against caller-trusted frozen Hub inputs.

    Payload has exactly node and edge. Node fields are candidateID, class,
    inventoryId, label, evidence. Edge fields are candidateID, relation,
    inventoryId, sourceID, targetCandidateID, evidence. Each evidence fragment
    supplies sourceUnitID, evidenceText, optional locatorAnchor and contribution.
    For multiple fragments, each contribution must be a nonempty string: it is
    preserved as an unverified claim, never interpreted as semantic support.
    All other source metadata/coordinates are forbidden in candidate input.

    Every quotation is independently passed to the unchanged Hub binder. Its
    verified page/Section provenance and original coordinates are retained, as
    are individual failures. Partial successful bindings do not validate an
    assertion. IDs namespace proposal identifiers by accepted page and content
    hash; they are source-local records, never canonical ontology instances.

    Validated means structural/literal checks only. No semantic gate is attested;
    a coherent substantive procedure remains not evaluated. An invalid, held or
    unresolved node prevents a validated edge, without discarding edge findings.
    """
    result: dict[str, Any] = {
        "contractID": CONTRACT_ID, "ontologyVersion": "0.1.6",
        "validationScope": "structure_and_literal_evidence_only",
        "semanticStatus": "not_evaluated", "graphAcceptance": False, "kgAuthorization": False,
        "originalPayload": deepcopy(payload), "source": None, "candidates": [], "diagnostics": [],
    }
    failed = "failed_source_or_evidence_binding"

    def stop(status: str, reason: str) -> dict[str, Any]:
        """Return a source/schema failure without asserting semantic absence."""
        result["status"] = status
        result["diagnostics"].append({"disposition": status, "reason": reason})
        return result

    if not isinstance(page, Mapping) or not isinstance(reader_result, Mapping):
        return stop(failed, "trusted_source_missing_or_malformed")
    if reader_result.get("status") != "source_read_success":
        if isinstance(reader_result.get("diagnostics"), list):
            result["diagnostics"].extend(deepcopy(reader_result["diagnostics"]))
        return stop(failed, "source_read_not_successful")
    replay = read_page_source_units(page, accepted_section_mapping=accepted_section_mapping)
    if replay["status"] != "source_read_success":
        result["diagnostics"].extend(deepcopy(replay["diagnostics"]))
        return stop(failed, "authority_verification_failed")
    url = page["canonical_url"]
    try:
        expected_id = "hub:page:" + hashlib.sha256(url.encode("utf-8")).hexdigest()[:20]
    except UnicodeEncodeError:
        return stop(failed, "page_identity_malformed")
    if accepted_page_id != expected_id or page["page_key"] != "hub-page:" + url:
        return stop(failed, "accepted_page_identity_mismatch")
    if reader_result.get("authority") != replay["authority"]:
        return stop(failed, "authority_provenance_mismatch")
    result["source"] = {key: deepcopy(value) for key, value in replay["authority"].items() if key != "text"}
    result["source"]["acceptedPageID"] = accepted_page_id
    if not isinstance(payload, Mapping) or set(payload) != {"node", "edge"}:
        return stop("rejected_invalid_assertion", "candidate_payload_fields_invalid")
    profile = get_profile("ciroh_hub")
    procedure = profile["entities"]["A-DC05"]["declaration"]
    relation = profile["relations"]["C-DC20"]["declaration"]

    def check(kind: str, supplied: Any) -> dict[str, Any]:
        """Check one assertion, retaining separate fragment and dependency results."""
        record: dict[str, Any] = {
            "kind": kind, "originalCandidate": deepcopy(supplied), "sourceLocalCandidateID": None,
            "findings": [], "evidenceBindings": [], "boundEvidence": [],
            "semanticStatus": "not_evaluated", "kgAuthorization": False,
        }

        def finding(reason: str, disposition: str = "rejected_invalid_assertion", **context: Any) -> None:
            """Retain each failure or review reason without repairing the proposal."""
            record["findings"].append({"reason": reason, "disposition": disposition, **context})

        if not isinstance(supplied, Mapping):
            finding("candidate_missing_or_malformed")
        else:
            fields = ({"candidateID", "class", "inventoryId", "label", "evidence"} if kind == "node" else
                      {"candidateID", "relation", "inventoryId", "sourceID", "targetCandidateID", "evidence"})
            required = fields - {"targetCandidateID"} if kind == "edge" else fields
            if set(supplied) - fields or required - set(supplied):
                finding("candidate_fields_invalid")
            cid = supplied.get("candidateID")
            if not isinstance(cid, str) or not cid.strip():
                finding("candidate_id_missing_or_malformed")
            else:
                identity = json.dumps([accepted_page_id, page["content_sha256"], kind, cid],
                                      ensure_ascii=True, separators=(",", ":"))
                record["sourceLocalCandidateID"] = "hub:candidate:" + hashlib.sha256(identity.encode()).hexdigest()
            identifier = supplied.get("inventoryId")
            identifier = identifier if isinstance(identifier, str) else ""
            if kind == "node":
                allowed = (supplied.get("class"), identifier) == (procedure["name"], procedure["id"])
                if not allowed:
                    finding("class_not_allowed")
                if not isinstance(supplied.get("label"), str) or not supplied["label"].strip():
                    finding("procedure_label_missing_or_malformed")
                scope = check_target("ciroh_hub", identifier)
            else:
                allowed = (supplied.get("relation"), identifier) == (relation["name"], relation["id"])
                if not allowed:
                    finding("relation_not_allowed")
                owner_bound = supplied.get("sourceID") == accepted_page_id
                if not owner_bound:
                    finding("source_endpoint_owner_or_direction_mismatch")
                node, target = payload["node"], supplied.get("targetCandidateID")
                node_valid = result["candidates"][0]["disposition"] == "validated"
                if target is None or target == "":
                    finding("target_endpoint_missing", "unresolved_endpoint")
                elif not isinstance(target, str):
                    finding("target_endpoint_malformed")
                elif not isinstance(node, Mapping) or target != node.get("candidateID"):
                    finding("target_endpoint_unresolved", "unresolved_endpoint")
                elif not node_valid:
                    finding("target_candidate_not_validated", "unresolved_endpoint")
                bound = (owner_bound and node_valid and isinstance(node, Mapping)
                         and target == node.get("candidateID"))
                record["endpointsBound"] = bound
                scope = check_target("ciroh_hub", identifier, relation_name=supplied.get("relation"),
                    source_class_id=profile["ownerClassID"] if owner_bound else None,
                    target_class_id=procedure["id"] if bound else None)
            record["targetProfileCheck"] = {
                "artifactFamily": "ciroh_hub", "inventoryId": identifier, "profileResult": scope,
                "targetStructuralCompatibility": allowed and not scope["reasons"],
                "pendingGates": list(scope["missingGates"]),
            }
            if scope["reasons"] and not record["findings"]:
                finding("target_profile_incompatible")
            if scope["missingGates"]:
                finding("target_profile_gates_pending", "needs_review")
            evidence = supplied.get("evidence")
            if not isinstance(evidence, list) or not evidence:
                finding("independent_evidence_missing_or_malformed")
            else:
                for index, fragment in enumerate(evidence):
                    if (not isinstance(fragment, Mapping)
                            or set(fragment) - {"sourceUnitID", "evidenceText", "locatorAnchor", "contribution"}
                            or not isinstance(fragment.get("sourceUnitID"), str) or not fragment["sourceUnitID"].strip()):
                        finding("evidence_fields_invalid", fragmentIndex=index)
                        continue
                    if ((len(evidence) > 1 or "contribution" in fragment)
                            and (not isinstance(fragment.get("contribution"), str) or not fragment["contribution"].strip())):
                        finding("fragment_contribution_missing_or_malformed", fragmentIndex=index)
                    quote = {key: deepcopy(fragment[key]) for key in ("evidenceText", "locatorAnchor") if key in fragment}
                    binding = bind_hub_evidence(page, reader_result, fragment["sourceUnitID"], [quote],
                        accepted_page_id=accepted_page_id, accepted_section_mapping=accepted_section_mapping)
                    record["evidenceBindings"].append({"fragmentIndex": index,
                        "originalFragment": deepcopy(fragment), "binding": binding})
                    if binding["status"] == "evidence_bound":
                        record["boundEvidence"].extend({**deepcopy(span), "fragmentIndex": index}
                                                       for span in binding["evidenceSpans"])
                    else:
                        for diagnostic in binding["diagnostics"]:
                            finding(diagnostic["reason"], binding["status"], fragmentIndex=index,
                                    bindingDiagnostic=deepcopy(diagnostic))
        dispositions = {f["disposition"] for f in record["findings"]}
        record["disposition"] = next((status for status in (
            failed, "rejected_invalid_assertion", "needs_review", "unresolved_endpoint")
            if status in dispositions), "validated")
        return record

    result["candidates"].append(check("node", payload["node"]))
    result["candidates"].append(check("edge", payload["edge"]))
    for record in result["candidates"]:
        result["diagnostics"].extend({"kind": record["kind"], **deepcopy(f)} for f in record["findings"])
    result["status"] = "candidate_checks_completed"
    return result


def validate_hub_candidates(
    page: Mapping[str, Any], reader_result: Mapping[str, Any], payload: Mapping[str, Any], *,
    accepted_page_id: str, accepted_section_mapping: Mapping[str, Any] | None = None,
    accepted_endpoints: list[Mapping[str, Any]] | None = None,
    accepted_assertions: list[Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    """Check a page-local batch without accepting semantics or writing assertions.

    Envelope: candidateNodes/candidateEdges, with unique candidateID across both.
    Nodes supply inventoryId/class/label/evidence and optional exact endpoint.
    Edges supply inventoryId/relation/source/target/evidence. Endpoint references
    are {referenceType: accepted_endpoint|candidate_node, referenceID: exact ID}.
    Trusted endpoints have endpointID/inventoryId/class; trusted assertions have
    assertionID/inventoryId/relation/sourceID/targetID, referencing those endpoints.

    Step, Example and Parameter nodes additionally supply parentPath: ordered
    references (candidate_edge or accepted_assertion) from this page through
    hasProcedure, optionally hasStep, and finally their own attachment. These
    explicit paths are checked structurally, including each independent binding;
    they never attest semantic parent acceptance. All gates remain pending.
    Paths include the final attachment to avoid free-floating dependent nodes.
    Attachments to accepted dependent endpoints instead supply edge parentPath
    through their parent (the current attachment is appended only for checking).
    Cyclic structural dependencies are resolved by monotone failure propagation,
    never by assuming acceptance. Candidate order does not determine survival.

    Evidence uses the existing Procedure fragment format. Fences bind only for
    Example/hasExample, as possible context. Parameter requires non-heading prose
    context and retains the unevaluated explanatory-prose gate. Duplicate records
    keep all original fragments. Only identifiable local failures are isolated.
    """
    from src.extraction.llm.documents.example_context_binding import bind_example_context

    result: dict[str, Any] = {"contractID": CONTRACT_ID, "ontologyVersion": "0.1.6",
        "originalPayload": deepcopy(payload), "candidateChecks": [], "diagnostics": [],
        "sourceDiagnostics": [], "inputComplete": False, "semanticStatus": "not_evaluated",
        "kgAuthorization": False, "graphAcceptance": False,
        "validationScope": "structure_and_literal_evidence_only"}

    def text(value: Any) -> bool:
        """Require an exact nonempty string without normalization."""
        return isinstance(value, str) and bool(value.strip())

    def stop(reason: str, status: str = "processing_failed") -> dict[str, Any]:
        """Retain global failures without inferring semantic abstention."""
        result["status"] = status
        result["diagnostics"].append({"reason": reason, "disposition": status})
        return result

    if (not isinstance(payload, Mapping) or set(payload) != {"candidateNodes", "candidateEdges"}
            or any(not isinstance(payload[k], list) for k in payload)):
        return stop("candidate_envelope_malformed")
    rows = payload["candidateNodes"] + payload["candidateEdges"]
    if any(not isinstance(r, Mapping) or not text(r.get("candidateID")) for r in rows):
        return stop("candidate_unidentifiable")
    if len({r["candidateID"] for r in rows}) != len(rows):
        return stop("candidate_identity_ambiguous")
    # Reuse the compatible entry point's authority checks even for an empty batch.
    preflight = validate_procedure_candidate(page, reader_result, {}, accepted_page_id=accepted_page_id,
                                             accepted_section_mapping=accepted_section_mapping)
    if preflight["source"] is None:
        result["diagnostics"] = deepcopy(preflight["diagnostics"])
        return stop("shared_authority_verification_failed", "failed_source_or_evidence_binding")
    if any(not isinstance(reader_result.get(k), list) for k in ("sourceUnits", "diagnostics")):
        return stop("trusted_reader_malformed")
    result["source"] = deepcopy(preflight["source"])
    result["sourceDiagnostics"] = deepcopy(reader_result["diagnostics"])
    replay = read_page_source_units(page, accepted_section_mapping=accepted_section_mapping)
    result["inputComplete"] = not reader_result["diagnostics"] and reader_result["sourceUnits"] == replay["sourceUnits"]
    profile = get_profile("ciroh_hub")
    endpoints = {accepted_page_id: {"endpointID": accepted_page_id, "inventoryId": "A-DC01", "class": "DocumentationPage"}}
    if any(v is not None and not isinstance(v, list) for v in (accepted_endpoints, accepted_assertions)):
        return stop("trusted_inventory_malformed")
    for row in accepted_endpoints or []:
        if not isinstance(row, Mapping) or not text(row.get("endpointID")):
            return stop("trusted_endpoint_unidentifiable")
        eid = row["endpointID"]
        if eid in endpoints:
            return stop("trusted_endpoint_identity_ambiguous")
        policy = profile["entities"].get(row.get("inventoryId")) if text(row.get("inventoryId")) else None
        endpoints[eid] = deepcopy(row) if policy and row.get("class") == policy["declaration"]["name"] else None
    scope_cache: dict[tuple, dict] = {}

    def scope(identifier: str, **kwargs: Any) -> dict:
        """Cache unchanged frozen-profile checks; never supply gate attestations."""
        if "relation_name" in kwargs and not isinstance(kwargs["relation_name"], str):
            kwargs["relation_name"] = None
        key = (identifier, *sorted(kwargs.items()))
        if key not in scope_cache:
            scope_cache[key] = check_target("ciroh_hub", identifier, **kwargs)
        return deepcopy(scope_cache[key])

    assertions = {}
    accepted_keys: dict[tuple, list[str]] = {}
    for row in accepted_assertions or []:
        if not isinstance(row, Mapping) or any(not text(row.get(k)) for k in
                ("assertionID", "inventoryId", "relation", "sourceID", "targetID")):
            return stop("accepted_assertion_malformed")
        if row["assertionID"] in assertions:
            return stop("accepted_assertion_identity_ambiguous")
        a, b = endpoints.get(row["sourceID"]), endpoints.get(row["targetID"])
        if not a or not b or scope(row["inventoryId"], relation_name=row["relation"],
                source_class_id=a["inventoryId"], target_class_id=b["inventoryId"])["reasons"]:
            return stop("accepted_assertion_signature_invalid")
        assertions[row["assertionID"]] = deepcopy(row)
        accepted_keys.setdefault((row["inventoryId"], row["sourceID"], row["targetID"]), []).append(row["assertionID"])
    records = {}
    for kind, group in (("node", payload["candidateNodes"]), ("edge", payload["candidateEdges"])):
        for row in group:
            identity = json.dumps([accepted_page_id, page["content_sha256"], kind, row["candidateID"]],
                                  ensure_ascii=True, separators=(",", ":"))
            rec = {"kind": kind, "candidateID": row["candidateID"], "originalCandidate": deepcopy(row),
                "sourceLocalCandidateID": "hub:candidate:" + hashlib.sha256(identity.encode()).hexdigest(),
                "findings": [], "dependencies": [], "evidenceBindings": [], "boundEvidence": [],
                "semanticStatus": "not_evaluated", "kgAuthorization": False, "suppressedDuplicate": False}
            records[row["candidateID"]] = rec
            result["candidateChecks"].append(rec)

    def finding(rec: dict, reason: str, disposition: str = "rejected_invalid_assertion", **extra: Any) -> None:
        """Preserve independent reasons without altering authentic proposals."""
        rec["findings"].append({"reason": reason, "disposition": disposition, **deepcopy(extra)})

    def resolve(rec: dict, ref: Any, local: bool = True) -> dict | None:
        """Resolve only exact supplied endpoint IDs or explicit local node IDs."""
        if (not isinstance(ref, Mapping) or set(ref) != {"referenceType", "referenceID"}
                or not text(ref.get("referenceID"))):
            finding(rec, "endpoint_reference_malformed", "unresolved_endpoint")
            return None
        rid = ref["referenceID"]
        if ref["referenceType"] == "accepted_endpoint":
            endpoint = endpoints.get(rid)
        elif local and ref["referenceType"] == "candidate_node":
            parent = records.get(rid)
            endpoint = parent.get("resolvedEndpoint") if parent and parent["kind"] == "node" else None
            if parent and parent["kind"] == "node":
                rec["dependencies"].append(rid)
        else:
            endpoint = None
        if endpoint is None:
            finding(rec, "endpoint_unresolved", "unresolved_endpoint", referenceID=rid)
        return deepcopy(endpoint)

    for rec in result["candidateChecks"]:
        row, kind = rec["originalCandidate"], rec["kind"]
        identifier = row.get("inventoryId") if text(row.get("inventoryId")) else ""
        policy = profile["entities" if kind == "node" else "relations"].get(identifier)
        fields = ({"candidateID", "inventoryId", "class", "label", "evidence", "endpoint"} if kind == "node" else
                  {"candidateID", "inventoryId", "relation", "source", "target", "evidence"})
        if (kind == "node" and identifier in {"A-DC06", "A-DC08", "A-DOM12"}
                or kind == "edge" and identifier in {"C-DC10", "C-DC12", "C-DC11"}):
            fields.add("parentPath")
        if set(row) - fields or fields - {"endpoint", "parentPath"} - set(row):
            finding(rec, "candidate_fields_invalid")
        name = "class" if kind == "node" else "relation"
        if not policy or row.get(name) != policy["declaration"]["name"]:
            finding(rec, "target_not_allowed")
        if kind == "node":
            external = resolve(rec, row["endpoint"], False) if "endpoint" in row else None
            if not text(row.get("label")):
                finding(rec, "node_label_missing_or_malformed")
            if external and external["inventoryId"] != identifier:
                finding(rec, "node_endpoint_type_mismatch")
            if policy and not policy["modelAuthorable"] and external is None:
                finding(rec, "exact_endpoint_required", "unresolved_endpoint")
            rec["resolvedEndpoint"] = external or ({"endpointID": rec["sourceLocalCandidateID"],
                "inventoryId": identifier, "class": row.get("class")} if policy and policy["modelAuthorable"] else None)
            checked = scope(identifier, model_authored=external is None)
            if external:
                rec["duplicateOf"] = [external["endpointID"]]
        else:
            source, target = resolve(rec, row.get("source")), resolve(rec, row.get("target"))
            rec["resolvedSource"], rec["resolvedTarget"] = source, target
            checked = scope(identifier, relation_name=row.get("relation"),
                source_class_id=source["inventoryId"] if source else None,
                target_class_id=target["inventoryId"] if target else None)
        if checked["reasons"]:
            finding(rec, "target_profile_incompatible", profileReasons=checked["reasons"])
        rec["targetProfileCheck"] = {"profileResult": checked, "pendingGates": checked["missingGates"],
            "targetStructuralCompatibility": bool(policy) and not checked["reasons"]
                and row.get(name) == policy["declaration"]["name"]
                and (kind != "node" or external is None or external["inventoryId"] == identifier)}
        if checked["missingGates"]:
            finding(rec, "semantic_gates_pending", "unresolved_condition", gates=checked["missingGates"])
        evidence = row.get("evidence")
        if not isinstance(evidence, list) or not evidence:
            finding(rec, "independent_evidence_missing_or_malformed")
            continue
        parameter_prose_bound = False
        for index, fragment in enumerate(evidence):
            if (not isinstance(fragment, Mapping) or set(fragment) - {"sourceUnitID", "evidenceText", "locatorAnchor", "contribution"}
                    or not text(fragment.get("sourceUnitID"))):
                finding(rec, "evidence_fields_invalid", fragmentIndex=index)
                continue
            if (len(evidence) > 1 or "contribution" in fragment) and not text(fragment.get("contribution")):
                finding(rec, "fragment_contribution_missing_or_malformed", fragmentIndex=index)
            uid = fragment["sourceUnitID"]
            unit = next((u for u in replay["sourceUnits"] if u["sourceUnitID"] == uid), None)
            # Only explicitly disjoint technical diagnostics may be scoped away.
            scoped = []
            for diagnostic in reader_result["diagnostics"]:
                unrelated = False
                if unit and isinstance(diagnostic, Mapping) and diagnostic.get("status") == "failed_source_or_evidence_binding":
                    ref = diagnostic.get("sourceUnitID")
                    first = diagnostic.get("startLine", diagnostic.get("sourceLine"))
                    last = diagnostic.get("endLine", first)
                    disjoint = type(first) is int and type(last) is int and 1 <= first <= last and (
                        last < unit["startLine"] or first > unit["endLine"])
                    unrelated = (ref is not None and ref != uid and first is None) or (disjoint and ref != uid)
                if not unrelated:
                    scoped.append(diagnostic)
            view = {**reader_result, "diagnostics": scoped}
            fence = unit and unit["contentKind"] == "fenced_snippet"
            binder = bind_example_context if fence and identifier in {"A-DC08", "C-DC12"} else bind_hub_evidence
            binding = binder(page, view, uid, [{k: fragment[k] for k in ("evidenceText", "locatorAnchor") if k in fragment}],
                accepted_page_id=accepted_page_id, accepted_section_mapping=accepted_section_mapping)
            rec["evidenceBindings"].append({"fragmentIndex": index, "originalFragment": deepcopy(fragment), "binding": binding})
            if binding["status"] in {"evidence_bound", "example_context_bound"}:
                rec["boundEvidence"].extend({**deepcopy(s), "fragmentIndex": index} for s in binding["evidenceSpans"])
                if binding["status"] == "example_context_bound":
                    rec["contextDisposition"] = "possible_example_context"
                if unit and unit["contentKind"] in {"prose", "list_text", "table_text", "component_text"}:
                    parameter_prose_bound = True
            else:
                for diagnostic in binding["diagnostics"]:
                    finding(rec, diagnostic["reason"], binding["status"], fragmentIndex=index, bindingDiagnostic=diagnostic)
                if any(d["reason"] != "evidence_quote_unbound" for d in binding["diagnostics"]):
                    result["inputComplete"] = False

        if identifier in {"A-DOM12", "C-DC11"} and not parameter_prose_bound:
            finding(rec, "parameter_explanatory_prose_required", "needs_review")

    # An attachment to a local dependent must agree with its declared path.
    # For an exact accepted dependent, the edge supplies the ancestry path to
    # its source; append this independently checked attachment in a detached view.
    path_records = []
    for rec in result["candidateChecks"]:
        row = rec["originalCandidate"]
        identifier = row.get("inventoryId") if text(row.get("inventoryId")) else ""
        if rec["kind"] == "node":
            path_records.append((rec, row, identifier, rec.get("resolvedEndpoint")))
        elif identifier in {"C-DC10", "C-DC12", "C-DC11"}:
            target_ref = row.get("target")
            target_node = (records.get(target_ref.get("referenceID")) if isinstance(target_ref, Mapping)
                           and target_ref.get("referenceType") == "candidate_node"
                           and text(target_ref.get("referenceID")) else None)
            path = target_node["originalCandidate"].get("parentPath") if target_node else row.get("parentPath")
            if not target_node and isinstance(path, list):
                path = path + [{"referenceType": "candidate_edge", "referenceID": rec["candidateID"]}]
            expected_type = {"C-DC10": "A-DC06", "C-DC12": "A-DC08", "C-DC11": "A-DOM12"}[identifier]
            path_records.append((rec, {"parentPath": path}, expected_type, rec.get("resolvedTarget")))

    # Explicit ordered paths are checked after all nodes and edges have bindings.
    for rec, row, identifier, endpoint in path_records:
        if identifier not in {"A-DC06", "A-DC08", "A-DOM12"}:
            continue
        path = row.get("parentPath")
        expected_last = {"A-DC06": "C-DC10", "A-DC08": "C-DC12", "A-DOM12": "C-DC11"}[identifier]
        relations, previous, last_edge = [], accepted_page_id, None
        valid = isinstance(path, list) and bool(path)
        for ref in path if isinstance(path, list) else []:
            edge = None
            if isinstance(ref, Mapping) and set(ref) == {"referenceType", "referenceID"} and text(ref.get("referenceID")):
                if ref["referenceType"] == "accepted_assertion":
                    edge = assertions.get(ref["referenceID"])
                elif ref["referenceType"] == "candidate_edge":
                    dependency = records.get(ref["referenceID"])
                    if dependency and dependency["kind"] == "edge":
                        rec["dependencies"].append(ref["referenceID"])
                        a, b = dependency.get("resolvedSource"), dependency.get("resolvedTarget")
                        if a and b:
                            edge = {"inventoryId": dependency["originalCandidate"].get("inventoryId"),
                                    "sourceID": a["endpointID"], "targetID": b["endpointID"]}
            if not edge:
                valid = False
                continue
            last_edge = edge
            relations.append(edge["inventoryId"])
            valid = valid and edge["sourceID"] == previous
            previous = edge["targetID"]
        allowed = [["C-DC20", expected_last]]
        if identifier != "A-DC06":
            allowed.append(["C-DC20", "C-DC10", expected_last])
        valid = valid and relations in allowed and endpoint is not None and previous == endpoint["endpointID"]
        if rec["kind"] == "edge":
            source = rec.get("resolvedSource")
            valid = valid and source is not None and last_edge is not None and last_edge["sourceID"] == source["endpointID"]
        rec["parentPathStructurallyLinked"] = bool(valid)
        if not valid:
            finding(rec, "required_parent_path_unresolved", "unresolved_endpoint")
        # Step's procedural acceptance is a contract condition even though the
        # frozen profile does not expose it as a named boolean gate.
        finding(rec, "parent_semantic_acceptance_not_evaluated", "unresolved_condition")

    def blocked(rec: dict) -> bool:
        """Pending semantic conditions are not structural failures."""
        return any(f["disposition"] != "unresolved_condition" for f in rec["findings"])

    changed = True
    while changed:
        changed = False
        for rec in result["candidateChecks"]:
            for dep in dict.fromkeys(rec["dependencies"]):
                if blocked(records[dep]) and not any(f.get("dependencyID") == dep for f in rec["findings"]):
                    finding(rec, "dependent_candidate_not_validated", "unresolved_endpoint", dependencyID=dep)
                    changed = True
    # Preserve unresolved semantics on every actual dependent without making
    # those pending gates a structural failure in the fixpoint above.
    changed = True
    while changed:
        changed = False
        for rec in result["candidateChecks"]:
            if not any(f["disposition"] == "unresolved_condition" for f in rec["findings"]) and any(
                    any(f["disposition"] == "unresolved_condition" for f in records[d]["findings"]) for d in rec["dependencies"]):
                finding(rec, "dependent_semantic_conditions_pending", "unresolved_condition")
                changed = True
    seen = {}
    for rec in result["candidateChecks"]:
        states = {f["disposition"] for f in rec["findings"]}
        rec["disposition"] = next((s for s in ("failed_source_or_evidence_binding", "rejected_invalid_assertion",
            "needs_review", "unresolved_endpoint", "unresolved_condition") if s in states), "validated")
        rec["validationDisposition"] = rec["disposition"]
        if not blocked(rec):
            if rec["kind"] == "edge":
                a, b = rec["resolvedSource"], rec["resolvedTarget"]
                key = rec["originalCandidate"]["inventoryId"], a["endpointID"], b["endpointID"]
                duplicates = accepted_keys.get(key, []) or ([seen[key]] if key in seen else [])
                if duplicates:
                    rec["duplicateOf"] = duplicates
                else:
                    seen[key] = rec["candidateID"]
            if rec.get("duplicateOf"):
                rec["suppressedDuplicate"] = True
                if rec["disposition"] == "validated":
                    rec["disposition"] = "suppressed_duplicate"
        result["diagnostics"].extend({"candidateID": rec["candidateID"], **deepcopy(f)} for f in rec["findings"])
    result["status"] = "candidate_checks_completed"
    return result
