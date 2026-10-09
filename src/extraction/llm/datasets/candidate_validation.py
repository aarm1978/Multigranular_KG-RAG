"""HydroShare batch validation with the compatible bounded Variable/C-D16 entry point.

Frozen authorities: Step 11 v0.3 §§2–3 and ontology v0.1.6. A literal match does
not establish that a quantity is measurable or contained in the dataset: those
semantic criteria remain unevaluated. No graph acceptance/materialization occurs.
"""

from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from typing import Any, Mapping

from src.extraction.llm.semantic_target_profiles import get_profile, check_target

from src.extraction.llm.datasets.source_units import (
    AbstractSourceUnit, CONTRACT_ID, bind_abstract_evidence, build_abstract_source_unit, bind_readme_evidence,
)


def validate_variable_candidate(
    unit: AbstractSourceUnit,
    payload: Mapping[str, Any],
    *,
    accepted_owner_id: str,
    trusted_provenance: Mapping[str, Any],
) -> dict[str, Any]:
    """Check one synthetic node/edge proposal against a caller-trusted unit.

    Payload has exactly ``provenance``, ``node`` and ``edge``. Provenance repeats
    resource_id, snapshotID, sourceVersion, sourceUnitID and authorityTextSha256.
    Node fields: candidateID, class, inventoryId, label, evidence. Edge fields:
    candidateID, relation, inventoryId, sourceID, targetCandidateID, evidence.
    Evidence is a nonempty list of evidenceText/optional locatorAnchor mappings,
    supplied independently for each assertion (the same quote may support both).

    Frozen profile checks read only the ontology specification. Profile reasons
    report structural incompatibility separately from pending gates; no gate is
    attested here. Existing validated dispositions still mean bounded structural
    and literal checks only, never semantic acceptance or KG authorization.

    The caller supplies trusted snapshotID and optional sourceVersion separately
    from the candidate payload. Unit self-consistency is rechecked through the
    unchanged builder, including its expected digest when supplied. Computed-only
    provenance never becomes an independent acquisition-integrity claim.

    Source-local IDs namespace supplied candidateIDs by unit and assertion kind;
    they identify proposal records, not canonical entities. Missing/unknown target
    references remain unresolved. All original input content is preserved in a
    detached copy; no assertion is repaired or rewritten.
    """
    result: dict[str, Any] = {
        "contractID": CONTRACT_ID, "ontologyVersion": "0.1.6",
        "validationScope": "structure_and_literal_evidence_only",
        "semanticStatus": "not_evaluated", "graphAcceptance": False, "kgAuthorization": False,
        "originalPayload": deepcopy(payload), "source": None,
        "candidates": [], "diagnostics": [],
    }

    def failure(reason: str) -> dict[str, Any]:
        """Stop on a technical input/provenance failure, preserving the payload."""
        result["status"] = "failed_source_or_evidence_binding"
        result["diagnostics"].append({"reason": reason, "disposition": result["status"]})
        return result

    if not isinstance(unit, AbstractSourceUnit):
        return failure("source_unit_missing_or_malformed")
    # Keep suspect provenance for diagnosis even when it cannot be trusted.
    result["source"] = {"resource_id": unit.resource_id, "snapshotID": unit.snapshot_id,
                        "sourceVersion": unit.source_version, "sourceUnitID": unit.source_unit_id,
                        "authorityTextSha256": unit.authority_text_sha256}
    if not isinstance(trusted_provenance, Mapping):
        return failure("trusted_provenance_missing_or_malformed")
    rebuilt = build_abstract_source_unit(
        {"resource_id": unit.resource_id, "abstract": unit.text},
        accepted_owner_id=accepted_owner_id, provenance=trusted_provenance,
        expected_authority_text_sha256=unit.expected_authority_text_sha256,
    )
    if rebuilt["status"] != "source_read_success":
        result["diagnostics"].append(deepcopy(rebuilt["diagnostic"]))
        return failure("source_unit_verification_failed")
    if unit != rebuilt["unit"]:
        return failure("source_unit_integrity_or_provenance_mismatch")
    result["source"] = unit.to_record()
    result["source"].pop("text")
    if not isinstance(payload, Mapping):
        return failure("candidate_payload_malformed")
    expected_provenance = {key: result["source"][key] for key in (
        "resource_id", "snapshotID", "sourceVersion", "sourceUnitID", "authorityTextSha256")}
    if payload.get("provenance") != expected_provenance:
        return failure("candidate_source_provenance_mismatch")
    if set(payload) != {"provenance", "node", "edge"}:
        result["status"] = "rejected_invalid_assertion"
        result["diagnostics"].append({"reason": "candidate_payload_fields_invalid", "disposition": result["status"]})
        return result

    profile = get_profile("hydroshare")
    variable = profile["entities"]["A-DOM04"]["declaration"]
    relation = profile["relations"]["C-D16"]["declaration"]

    def check(kind: str, supplied: Any) -> dict[str, Any]:
        """Validate one assertion and bind only its own supplied quotations."""
        record: dict[str, Any] = {"kind": kind, "originalCandidate": deepcopy(supplied),
                                  "sourceLocalCandidateID": None, "findings": [], "boundEvidence": []}

        def finding(reason: str, disposition: str = "rejected_invalid_assertion") -> None:
            """Retain every finding even if another failure takes precedence."""
            record["findings"].append({"reason": reason, "disposition": disposition})

        if not isinstance(supplied, Mapping):
            finding("candidate_missing_or_malformed")
        else:
            fields = ({"candidateID", "class", "inventoryId", "label", "evidence"} if kind == "node"
                      else {"candidateID", "relation", "inventoryId", "sourceID", "targetCandidateID", "evidence"})
            # A missing target is an unresolved endpoint, not a schema rejection.
            required = fields - {"targetCandidateID"} if kind == "edge" else fields
            if set(supplied) - fields or required - set(supplied):
                finding("candidate_fields_invalid")
            identifier = supplied.get("candidateID")
            if not isinstance(identifier, str) or not identifier.strip():
                finding("candidate_id_missing_or_malformed")
            else:
                identity = json.dumps([unit.source_unit_id, kind, identifier], ensure_ascii=True, separators=(",", ":"))
                record["sourceLocalCandidateID"] = "hydroshare:candidate:" + hashlib.sha256(identity.encode()).hexdigest()
            if kind == "node":
                if (supplied.get("class"), supplied.get("inventoryId")) != (variable["name"], variable["id"]):
                    finding("class_not_allowed")
                if not isinstance(supplied.get("label"), str) or not supplied["label"].strip():
                    finding("variable_label_missing_or_malformed")
            else:
                if (supplied.get("relation"), supplied.get("inventoryId")) != (relation["name"], relation["id"]):
                    finding("relation_not_allowed")
                if supplied.get("sourceID") != accepted_owner_id:
                    finding("source_endpoint_owner_or_direction_mismatch")
                target = supplied.get("targetCandidateID")
                node = payload.get("node")
                if target is None or target == "":
                    finding("target_endpoint_missing", "unresolved_endpoint")
                elif not isinstance(target, str):
                    finding("target_endpoint_malformed")
                elif not isinstance(node, Mapping) or target != node.get("candidateID"):
                    finding("target_endpoint_unresolved", "unresolved_endpoint")
                elif result["candidates"][0]["disposition"] != "validated":
                    finding("target_candidate_not_validated", "unresolved_endpoint")
            # Profile checks do not replace exact endpoint or independent evidence checks.
            identifier = supplied.get("inventoryId")
            identifier = identifier if isinstance(identifier, str) else ""
            if kind == "node":
                scope = check_target("hydroshare", identifier)
                compatible = (not scope["reasons"] and identifier == variable["id"]
                              and supplied.get("class") == variable["name"])
                endpoints_bound = None
            else:
                node = payload.get("node")
                endpoints_bound = (supplied.get("sourceID") == accepted_owner_id
                    and isinstance(node, Mapping)
                    and supplied.get("targetCandidateID") == node.get("candidateID")
                    and result["candidates"][0]["disposition"] == "validated")
                scope = check_target("hydroshare", identifier,
                    relation_name=supplied.get("relation"),
                    source_class_id=profile["ownerClassID"] if supplied.get("sourceID") == accepted_owner_id else None,
                    target_class_id=variable["id"] if endpoints_bound else None)
                compatible = not scope["reasons"] and identifier == relation["id"]
            record["targetProfileCheck"] = {
                "artifactFamily": "hydroshare", "inventoryId": identifier,
                "profileResult": scope, "targetStructuralCompatibility": compatible,
                "endpointsBound": endpoints_bound, "pendingGates": list(scope["missingGates"]),
                "semanticStatus": "not_evaluated", "kgAuthorization": False}
            # Preserve unresolved endpoint dispositions; signature failure caused by
            # a missing/invalid node must not turn them into rejected assertions.
            if not compatible and (kind == "node" or endpoints_bound) and not record["findings"]:
                finding("target_profile_incompatible")
            evidence = supplied.get("evidence")
            if not isinstance(evidence, list) or not evidence:
                finding("independent_evidence_missing_or_malformed")
            elif any(not isinstance(span, Mapping) or set(span) - {"evidenceText", "locatorAnchor"} for span in evidence):
                finding("evidence_fields_invalid")
            else:
                binding = bind_abstract_evidence(unit, evidence)
                record["evidenceBinding"] = binding
                if binding["status"] != "evidence_bound":
                    finding("evidence_quote_unbound", "failed_source_or_evidence_binding")
                else:
                    record["boundEvidence"] = binding["evidenceSpans"]
        dispositions = {f["disposition"] for f in record["findings"]}
        record["disposition"] = next((status for status in (
            "failed_source_or_evidence_binding", "rejected_invalid_assertion", "unresolved_endpoint")
            if status in dispositions), "validated")
        return record

    result["candidates"].append(check("node", payload["node"]))
    result["candidates"].append(check("edge", payload["edge"]))
    for record in result["candidates"]:
        result["diagnostics"].extend({"kind": record["kind"], **deepcopy(f)} for f in record["findings"])
    result["status"] = "candidate_checks_completed"
    return result


def validate_dataset_candidates(
    payload: Mapping[str, Any], *, accepted_owner_id: str,
    trusted_provenance: Mapping[str, Any], abstract_units: list[AbstractSourceUnit] | None = None,
    readme_results: list[Mapping[str, Any]] | None = None,
    accepted_endpoints: list[Mapping[str, Any]] | None = None,
    authorized_stubs: list[Mapping[str, Any]] | None = None,
    accepted_assertions: list[Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    """Validate an identifiable HydroShare batch, without semantic/KG acceptance.

    Payload contains candidateNodes and candidateEdges arrays, with globally unique
    candidateID strings. Nodes have class, inventoryId, label, evidence, and optional
    endpoint. Edges have relation, inventoryId, source, target, evidence. Endpoint
    references contain exactly referenceType/referenceID; types are accepted_endpoint,
    authorized_stub, candidate_node. The accepted owner is implicitly indexed.

    Trusted endpoint rows contain endpointID, inventoryId and class. Stubs additionally
    require resource_id, snapshotID, sourceVersion and authorizationID; only Repository
    stubs are admissible. This function consumes their exact IDs, never creates them.
    Repository nodes MUST reference a trusted endpoint/stub; other nodes may reference
    an exact accepted endpoint. New local nodes are never merged by label.

    Evidence fragments contain sourceUnitID/evidenceText, optional locatorAnchor and
    contribution. Multi-fragment contributions are required and preserved as unverified
    claims. Abstract units and README reader results are pipeline-owned inputs. Their
    owner/snapshot/version must match trusted_provenance; adapters check exact text.

    Accepted assertion rows contain assertionID, inventoryId, relation, sourceID,
    targetID. Only exact predicate/endpoints suppress duplicates; every proposal and
    supporting citation remains recorded. Pending semantic gates remain pending even
    when an equivalent accepted assertion exists. No caller/model gate flags are used.

    Unidentifiable responses fail globally. Identifiable failures stay local; only
    candidate_node references propagate failed/conditional node dispositions to edges.
    inputComplete describes supplied source-read/integrity coverage, not semantic
    completeness. Validated denotes structure and literal binding only, as in the
    legacy entry point.
    """
    result: dict[str, Any] = {"contractID": CONTRACT_ID, "ontologyVersion": "0.1.6",
        "originalPayload": deepcopy(payload), "candidateChecks": [], "diagnostics": [],
        "sourceDiagnostics": [], "inputComplete": True,
        "semanticStatus": "not_evaluated", "kgAuthorization": False, "graphAcceptance": False,
        "validationScope": "structure_and_literal_evidence_only"}

    def stop(reason: str) -> dict[str, Any]:
        """Fail globally only when the envelope or shared trusted context is unusable."""
        result["status"] = "processing_failed"
        result["diagnostics"].append({"reason": reason, "disposition": "processing_failed"})
        return result

    def nonempty(value: Any) -> bool:
        """Require an exact nonempty string without repairing its spelling."""
        return isinstance(value, str) and bool(value.strip())

    if (not nonempty(accepted_owner_id) or not isinstance(trusted_provenance, Mapping)
            or not nonempty(trusted_provenance.get("snapshotID"))
            or trusted_provenance.get("sourceVersion") is not None and not nonempty(trusted_provenance["sourceVersion"])):
        return stop("trusted_owner_or_snapshot_malformed")
    if (not isinstance(payload, Mapping) or set(payload) != {"candidateNodes", "candidateEdges"}
            or any(not isinstance(payload[k], list) for k in ("candidateNodes", "candidateEdges"))):
        return stop("candidate_envelope_malformed")
    rows = payload["candidateNodes"] + payload["candidateEdges"]
    if any(not isinstance(r, Mapping) or not nonempty(r.get("candidateID")) for r in rows):
        return stop("candidate_unidentifiable")
    ids = [r["candidateID"] for r in rows]
    if len(ids) != len(set(ids)):
        return stop("candidate_identity_ambiguous")
    if any(v is not None and not isinstance(v, list) for v in
           (abstract_units, readme_results, accepted_endpoints, authorized_stubs, accepted_assertions)):
        return stop("trusted_collection_malformed")
    profile = get_profile("hydroshare")
    snapshot, version = trusted_provenance["snapshotID"], trusted_provenance.get("sourceVersion")
    result["source"] = {"resource_id": accepted_owner_id, "snapshotID": snapshot, "sourceVersion": version}
    scope_cache: dict[tuple, dict[str, Any]] = {}

    def scope(identifier: str, model: bool = True, relation: Any = None,
              source: str | None = None, target: str | None = None) -> dict[str, Any]:
        """Reuse frozen profile checks locally; never attest semantic gates."""
        name = relation if isinstance(relation, str) else None
        key = identifier, model, name, source, target
        if key not in scope_cache:
            scope_cache[key] = check_target("hydroshare", identifier, model_authored=model,
                relation_name=name, source_class_id=source, target_class_id=target)
        return deepcopy(scope_cache[key])

    endpoints: dict[str, list[dict[str, Any]]] = {accepted_owner_id: [{
        "endpointID": accepted_owner_id, "inventoryId": profile["ownerClassID"],
        "class": "DatasetResource", "referenceType": "accepted_endpoint"}]}
    for collection, ref_type in ((accepted_endpoints or [], "accepted_endpoint"), (authorized_stubs or [], "authorized_stub")):
        for row in collection:
            if not isinstance(row, Mapping) or not nonempty(row.get("endpointID")):
                return stop("trusted_endpoint_unidentifiable")
            record = deepcopy(dict(row))
            identifier = row.get("inventoryId")
            target = profile["entities"].get(identifier) if isinstance(identifier, str) else None
            valid = target is not None and row.get("class") == target["declaration"]["name"]
            if ref_type == "authorized_stub":
                valid = (valid and identifier == "A-C01" and row.get("resource_id") == accepted_owner_id
                    and row.get("snapshotID") == snapshot and row.get("sourceVersion") == version
                    and nonempty(row.get("authorizationID")))
            record.update(referenceType=ref_type, trustedEndpointValid=valid)
            endpoints.setdefault(row["endpointID"], []).append(record)
    accepted_keys: dict[tuple[str, str, str], list[str]] = {}
    for row in accepted_assertions or []:
        if not isinstance(row, Mapping) or any(not nonempty(row.get(k)) for k in
                ("assertionID", "inventoryId", "relation", "sourceID", "targetID")):
            return stop("accepted_assertion_malformed")
        declaration = profile["relations"].get(row["inventoryId"], {}).get("declaration", {})
        if declaration.get("name") != row["relation"]:
            return stop("accepted_assertion_profile_mismatch")
        accepted_keys.setdefault((row["inventoryId"], row["sourceID"], row["targetID"]), []).append(row["assertionID"])

    sources: dict[str, list[tuple[str, Any, Mapping[str, Any], str | None]]] = {}

    def source_failure(reason: str, **context: Any) -> None:
        """Report partial source completeness without poisoning unrelated candidates."""
        result["inputComplete"] = False
        result["sourceDiagnostics"].append({"reason": reason, **deepcopy(context)})

    for unit in abstract_units or []:
        if not isinstance(unit, AbstractSourceUnit) or not nonempty(unit.source_unit_id):
            source_failure("abstract_source_malformed")
            continue
        rebuilt = build_abstract_source_unit({"resource_id": unit.resource_id, "abstract": unit.text},
            accepted_owner_id=accepted_owner_id, provenance=trusted_provenance,
            expected_authority_text_sha256=unit.expected_authority_text_sha256)
        error = None if rebuilt.get("unit") == unit else "abstract_integrity_or_provenance_mismatch"
        if error:
            source_failure(error, sourceUnitID=unit.source_unit_id)
        sources.setdefault(unit.source_unit_id, []).append(("abstract", unit, unit.to_record() if error is None else {}, error))
    for reader in readme_results or []:
        if not isinstance(reader, Mapping):
            source_failure("readme_result_malformed")
            continue
        if reader.get("status") == "optional_input_absent":
            continue
        authority, units = reader.get("authority"), reader.get("sourceUnits")
        if reader.get("status") != "source_read_success" or not isinstance(authority, Mapping) or not isinstance(units, list):
            source_failure("readme_read_failed", diagnostics=reader.get("diagnostics", []))
            continue
        error = None
        if (authority.get("resource_id") != accepted_owner_id or authority.get("canonicalArtifactID") != accepted_owner_id
                or authority.get("snapshotID") != snapshot or authority.get("sourceVersion") != version):
            error = "readme_owner_or_snapshot_mismatch"
            source_failure(error)
        for unit in units:
            if not isinstance(unit, Mapping) or not nonempty(unit.get("sourceUnitID")):
                source_failure("readme_unit_unidentifiable")
                continue
            sources.setdefault(unit["sourceUnitID"], []).append(("README", reader, unit, error))
    for uid, entries in sources.items():
        if len(entries) != 1:
            source_failure("source_unit_identity_ambiguous", sourceUnitID=uid)

    node_checks: dict[str, dict[str, Any]] = {}
    seen_edges: dict[tuple[str, str, str], str] = {}

    def check(kind: str, row: Mapping[str, Any]) -> dict[str, Any]:
        """Bind independent evidence and retain every local failure/dependency."""
        evidence = row.get("evidence")
        unit_ids = sorted({f["sourceUnitID"] for f in evidence if isinstance(f, Mapping)
                           and isinstance(f.get("sourceUnitID"), str)}) if isinstance(evidence, list) else []
        identity = json.dumps([accepted_owner_id, snapshot, version, kind, row["candidateID"], unit_ids],
                              ensure_ascii=True, separators=(",", ":"))
        record: dict[str, Any] = {"kind": kind, "candidateID": row["candidateID"], "originalCandidate": deepcopy(row),
            "sourceLocalCandidateID": "hydroshare:batch-candidate:" + hashlib.sha256(identity.encode()).hexdigest(),
            "findings": [], "boundEvidence": [], "evidenceBindings": [], "dependencies": [],
            "semanticStatus": "not_evaluated", "kgAuthorization": False, "suppressedDuplicate": False}

        def finding(reason: str, disposition: str = "rejected_invalid_assertion", **extra: Any) -> None:
            """Keep reasons even if another failure takes disposition precedence."""
            record["findings"].append({"reason": reason, "disposition": disposition, **deepcopy(extra)})

        def resolve(reference: Any, allow_candidate: bool = True) -> dict[str, Any] | None:
            """Resolve exact trusted references; never use labels, URLs or fuzzy IDs."""
            if (not isinstance(reference, Mapping) or set(reference) != {"referenceType", "referenceID"}
                    or not nonempty(reference.get("referenceID")) or not isinstance(reference.get("referenceType"), str)):
                finding("endpoint_reference_missing_or_malformed", "unresolved_endpoint")
                return None
            ref_type, ref_id = reference.get("referenceType"), reference["referenceID"]
            if ref_type == "candidate_node" and allow_candidate:
                parent = node_checks.get(ref_id)
                record["dependencies"].append(ref_id)
                if parent is None or parent.get("resolvedEndpoint") is None:
                    finding("candidate_endpoint_unresolved", "unresolved_endpoint", referenceID=ref_id)
                    return None
                if parent["disposition"] not in {"validated", "suppressed_duplicate"}:
                    finding("dependent_node_not_validated", "unresolved_endpoint", referenceID=ref_id,
                            parentDisposition=parent["disposition"])
                return deepcopy(parent["resolvedEndpoint"])
            if ref_type not in {"accepted_endpoint", "authorized_stub"}:
                finding("endpoint_reference_type_invalid")
                return None
            matches = endpoints.get(ref_id, [])
            if len(matches) != 1 or matches[0].get("referenceType") != ref_type or matches[0].get("trustedEndpointValid") is False:
                finding("trusted_endpoint_missing_invalid_or_ambiguous", "unresolved_endpoint", referenceID=ref_id)
                return None
            return deepcopy(matches[0])

        identifier = row.get("inventoryId")
        identifier = identifier if isinstance(identifier, str) else ""
        policy = (profile["entities"] if kind == "node" else profile["relations"]).get(identifier)
        fields = ({"candidateID", "class", "inventoryId", "label", "evidence", "endpoint"} if kind == "node"
                  else {"candidateID", "relation", "inventoryId", "source", "target", "evidence"})
        required = fields - ({"endpoint"} if kind == "node" else {"source", "target"})
        if set(row) - fields or required - set(row):
            finding("candidate_fields_invalid")
        if kind == "node":
            external = resolve(row["endpoint"], False) if "endpoint" in row else None
            if not nonempty(row.get("label")):
                finding("node_label_missing_or_malformed")
            profile_check = scope(identifier, model=external is None)
            if policy is None or row.get("class") != policy["declaration"]["name"]:
                finding("class_not_allowed")
            if external is not None and external["inventoryId"] != identifier:
                finding("node_endpoint_type_mismatch")
            if policy is not None and not policy["modelAuthorable"] and external is None:
                finding("exact_endpoint_required", "unresolved_endpoint")
            record["resolvedEndpoint"] = external if external is not None else (
                {"endpointID": record["sourceLocalCandidateID"], "inventoryId": identifier,
                 "class": row.get("class"), "referenceType": "candidate_node"}
                if policy is not None and policy["modelAuthorable"] and row.get("class") == policy["declaration"]["name"] else None)
            if external is not None and external["referenceType"] == "accepted_endpoint":
                record["duplicateOf"] = [external["endpointID"]]
        else:
            source, target = resolve(row.get("source")), resolve(row.get("target"))
            record["resolvedSource"], record["resolvedTarget"] = source, target
            if source is not None and source["endpointID"] != accepted_owner_id:
                finding("source_endpoint_owner_or_direction_mismatch")
            profile_check = scope(identifier, relation=row.get("relation"),
                source=source["inventoryId"] if source else None, target=target["inventoryId"] if target else None)
            if policy is None or row.get("relation") != policy["declaration"]["name"]:
                finding("relation_not_allowed")
        # Missing endpoints retain unresolved status; known wrong signatures reject.
        reasons = profile_check["reasons"]
        if reasons and not (kind == "edge" and (source is None or target is None)
                            and reasons == ["endpoint_signature_or_scope_mismatch"]):
            if not (kind == "node" and reasons == ["not_model_authorable"] and policy is not None):
                finding("target_profile_incompatible", profileReasons=reasons)
        record["targetProfileCheck"] = {"profileResult": profile_check,
            "targetStructuralCompatibility": (policy is not None and not reasons
                and row.get("class" if kind == "node" else "relation") == policy["declaration"]["name"]
                and (kind != "node" or external is None or external["inventoryId"] == identifier)),
            "pendingGates": list(profile_check["missingGates"])}
        if profile_check["missingGates"]:
            finding("semantic_gate_pending", "unresolved_condition", gates=profile_check["missingGates"])
        readme_only = identifier in {"A-D12", "C-D17"}
        if not isinstance(evidence, list) or not evidence:
            finding("independent_evidence_missing_or_malformed")
        else:
            for index, fragment in enumerate(evidence):
                if (not isinstance(fragment, Mapping) or set(fragment) - {"sourceUnitID", "evidenceText", "locatorAnchor", "contribution"}
                        or not nonempty(fragment.get("sourceUnitID"))):
                    finding("evidence_fields_invalid", fragmentIndex=index)
                    continue
                if (len(evidence) > 1 or "contribution" in fragment) and not nonempty(fragment.get("contribution")):
                    finding("fragment_contribution_missing_or_malformed", fragmentIndex=index)
                uid = fragment["sourceUnitID"]
                entries = sources.get(uid, [])
                if len(entries) != 1:
                    finding("source_unit_missing_or_ambiguous", "failed_source_or_evidence_binding", fragmentIndex=index)
                    continue
                channel, original, metadata, error = entries[0]
                if error:
                    finding(error, "failed_source_or_evidence_binding", fragmentIndex=index)
                    continue
                if readme_only and channel != "README":
                    finding("measurement_requires_readme_evidence", fragmentIndex=index)
                quote = {k: fragment[k] for k in ("evidenceText", "locatorAnchor") if k in fragment}
                binding = bind_abstract_evidence(original, [quote]) if channel == "abstract" else bind_readme_evidence(original, uid, [quote])
                record["evidenceBindings"].append({"fragmentIndex": index, "originalFragment": deepcopy(fragment), "binding": binding})
                if binding["status"] == "evidence_bound":
                    record["boundEvidence"].extend({**deepcopy(span), "fragmentIndex": index} for span in binding["evidenceSpans"])
                else:
                    diagnostics = binding.get("diagnostics", [binding.get("diagnostic", {"reason": "evidence_quote_unbound"})])
                    for diagnostic in diagnostics:
                        finding(diagnostic["reason"], "failed_source_or_evidence_binding", fragmentIndex=index,
                                bindingDiagnostic=diagnostic)
                    if any(d.get("reason") != "evidence_quote_unbound" for d in diagnostics):
                        source_failure("source_binding_verification_failed", sourceUnitID=uid)
        dispositions = {f["disposition"] for f in record["findings"]}
        record["disposition"] = next((s for s in ("failed_source_or_evidence_binding", "rejected_invalid_assertion",
            "unresolved_endpoint", "unresolved_condition") if s in dispositions), "validated")
        record["validationDisposition"] = record["disposition"]
        if kind == "edge" and source is not None and target is not None and record["disposition"] in {"validated", "unresolved_condition"}:
            key = identifier, source["endpointID"], target["endpointID"]
            duplicates = accepted_keys.get(key, []) or ([seen_edges[key]] if key in seen_edges else [])
            if duplicates:
                record["duplicateOf"] = list(duplicates)
            elif record["disposition"] == "validated":
                seen_edges[key] = row["candidateID"]
        if record.get("duplicateOf") and record["disposition"] in {"validated", "unresolved_condition"}:
            record["suppressedDuplicate"] = True
            if record["disposition"] == "validated":
                record["disposition"] = "suppressed_duplicate"
        return record

    for row in payload["candidateNodes"]:
        record = check("node", row)
        node_checks[row["candidateID"]] = record
        result["candidateChecks"].append(record)
    for row in payload["candidateEdges"]:
        result["candidateChecks"].append(check("edge", row))
    for record in result["candidateChecks"]:
        result["diagnostics"].extend({"candidateID": record["candidateID"], **deepcopy(f)} for f in record["findings"])
    result["status"] = "candidate_checks_completed"
    return result
