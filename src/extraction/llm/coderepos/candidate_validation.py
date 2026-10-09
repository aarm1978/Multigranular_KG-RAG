"""Offline GitHub batch checks under frozen Step 11 v0.3 §§2/4/6/7.

Structural/literal validation only. No semantic acceptance, provider execution,
Publication identity alignment, Step 14 resolution or graph materialization.
"""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json
import re
from typing import Any, Mapping

from src.extraction.llm.coderepos.evidence_binding import bind_repository_evidence
from src.extraction.llm.coderepos.purpose_validation import purpose_vocabulary, validate_purpose_candidates
from src.extraction.llm.semantic_target_profiles import CONTRACT_ID, get_profile, check_target


def validate_repository_candidates(
    reader_result: Mapping[str, Any], payload: Mapping[str, Any], *,
    accepted_repository: Mapping[str, Any], accepted_endpoints: list[Mapping[str, Any]] | None = None,
    accepted_assertions: list[Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    """Validate identifiable candidates; isolate only their actual dependencies.

    Payload has candidateNodes/candidateEdges lists with globally unique candidateID.
    Nodes: candidateID, inventoryId, class, label, evidence, optional endpoint.
    ModelVersion additionally requires productRepositoryID equal to the accepted
    owner; this untrusted declaration never proves the own-product semantic gate.
    Edges: candidateID, inventoryId, relation, source, target, evidence. C-C07 also
    supplies categoryKey and optionally classification/reason (legacy purpose rules).
    C-C16 may retain methodSurfaceForm/candidatePublicationIdentifier as unresolved
    hints; these never resolve an endpoint. References have referenceType/referenceID,
    either accepted_endpoint or candidate_node. No model-created stubs are supported.

    Evidence fragments carry sourceUnitID/evidenceText and optional locatorAnchor,
    contribution; multiple fragments require nonempty contributions, retained but
    not semantically evaluated. Each quote independently uses the accepted binder.
    Purpose candidates delegate unchanged quotes/category values to the accepted
    purpose validator, per verified unit. Its legacy disposition is retained.

    Trusted endpoint rows have endpointID/inventoryId/class. DatasetResource and
    Method require exact supplied endpoints; controlled purpose seeds are generated
    only by purpose_vocabulary(). ModelVersion endpoint rows also need trusted
    productRepositoryID. Method typing alone is never accepted Publication provenance.
    Accepted assertions have assertionID/inventoryId/relation/sourceID/targetID.
    Exact duplicates retain citations and pending gates; names never merge nodes.

    All semantic gates remain pending. implementsMethod always stays unresolved
    here: later authorized resolution is a different stage. inputComplete describes
    supplied source coverage, never semantic completeness or absence of evidence.
    """
    result: dict[str, Any] = {"contractID": CONTRACT_ID, "ontologyVersion": "0.1.6",
        "originalPayload": deepcopy(payload), "candidateChecks": [], "diagnostics": [],
        "sourceDiagnostics": [], "inputComplete": False, "semanticStatus": "not_evaluated",
        "kgAuthorization": False, "graphAcceptance": False,
        "validationScope": "structure_and_literal_evidence_only"}

    def nonempty(value: Any) -> bool:
        """Check string identity without normalizing or repairing it."""
        return isinstance(value, str) and bool(value.strip())

    def stop(reason: str) -> dict[str, Any]:
        """Stop globally on an unidentifiable response or malformed shared context."""
        result["status"] = "processing_failed"
        result["diagnostics"].append({"reason": reason, "disposition": "processing_failed"})
        return result

    if (not isinstance(payload, Mapping) or set(payload) != {"candidateNodes", "candidateEdges"}
            or any(not isinstance(payload[k], list) for k in ("candidateNodes", "candidateEdges"))):
        return stop("candidate_envelope_malformed")
    rows = payload["candidateNodes"] + payload["candidateEdges"]
    if any(not isinstance(r, Mapping) or not nonempty(r.get("candidateID")) for r in rows):
        return stop("candidate_unidentifiable")
    if len({r["candidateID"] for r in rows}) != len(rows):
        return stop("candidate_identity_ambiguous")
    if (not isinstance(accepted_repository, Mapping) or type(accepted_repository.get("repo_id")) is not int
            or accepted_repository.get("canonicalArtifactID") != f"github:repo:{accepted_repository.get('repo_id')}"
            or not nonempty(accepted_repository.get("full_name")) or not isinstance(accepted_repository.get("frozenCommitSha"), str)
            or not re.fullmatch(r"[0-9a-fA-F]{40}", accepted_repository["frozenCommitSha"])):
        return stop("trusted_repository_malformed")
    if not isinstance(reader_result, Mapping) or any(not isinstance(reader_result.get(k), list)
            for k in ("sourceUnits", "authorities", "reads", "diagnostics")):
        return stop("trusted_reader_malformed")
    if any(c is not None and not isinstance(c, list) for c in (accepted_endpoints, accepted_assertions)):
        return stop("trusted_endpoint_inventory_malformed")
    result["source"] = deepcopy(accepted_repository)
    result["sourceDiagnostics"] = deepcopy(reader_result["diagnostics"])
    result["inputComplete"] = reader_result.get("inputComplete") is True and not reader_result["diagnostics"]
    profile = get_profile("github")
    vocabulary = purpose_vocabulary()
    result["vocabularyRecords"] = vocabulary
    owner = accepted_repository["canonicalArtifactID"]
    endpoints: dict[str, list[dict[str, Any]]] = {owner: [{"endpointID": owner, "inventoryId": "A-C01", "class": "Repository"}]}
    for seed in vocabulary:
        endpoints[seed["nodeID"]] = [{"endpointID": seed["nodeID"], "inventoryId": seed["inventoryId"],
                                     "class": seed["class"], "seedRecord": deepcopy(seed)}]
    for row in accepted_endpoints or []:
        if not isinstance(row, Mapping) or not nonempty(row.get("endpointID")):
            return stop("trusted_endpoint_unidentifiable")
        if row["endpointID"] in {owner, *(s["nodeID"] for s in vocabulary)}:
            return stop("trusted_endpoint_reserved_identity_collision")
        identifier = row.get("inventoryId")
        policy = profile["entities"].get(identifier) if isinstance(identifier, str) else None
        valid = policy is not None and row.get("class") == policy["declaration"]["name"] and identifier != "A-C07"
        if identifier == "A-C10":
            valid = valid and row.get("productRepositoryID") == owner
        endpoints.setdefault(row["endpointID"], []).append({**deepcopy(row), "trustedEndpointValid": valid})
    accepted_keys: dict[tuple, list[str]] = {}
    for row in accepted_assertions or []:
        if not isinstance(row, Mapping) or any(not nonempty(row.get(k)) for k in
                ("assertionID", "inventoryId", "relation", "sourceID", "targetID")):
            return stop("accepted_assertion_malformed")
        if profile["relations"].get(row["inventoryId"], {}).get("declaration", {}).get("name") != row["relation"]:
            return stop("accepted_assertion_profile_mismatch")
        accepted_keys.setdefault((row["inventoryId"], row["sourceID"], row["targetID"]), []).append(row["assertionID"])
    cache: dict[tuple, dict[str, Any]] = {}
    nodes: dict[str, dict[str, Any]] = {}
    seen: dict[tuple, str] = {}

    def scope(identifier: str, model: bool = True, relation: Any = None,
              source: str | None = None, target: str | None = None) -> dict[str, Any]:
        """Reuse frozen declarations and signatures without ever supplying gates."""
        name = relation if isinstance(relation, str) else None
        key = identifier, model, name, source, target
        if key not in cache:
            cache[key] = check_target("github", identifier, model_authored=model, relation_name=name,
                                      source_class_id=source, target_class_id=target)
        return deepcopy(cache[key])

    def check(kind: str, row: Mapping[str, Any]) -> dict[str, Any]:
        """Check one identifiable assertion and retain its independent bindings."""
        identifier = row.get("inventoryId") if isinstance(row.get("inventoryId"), str) else ""
        policy = (profile["entities"] if kind == "node" else profile["relations"]).get(identifier)
        evidence = row.get("evidence")
        uids = sorted({e["sourceUnitID"] for e in evidence if isinstance(e, Mapping)
                       and isinstance(e.get("sourceUnitID"), str)}) if isinstance(evidence, list) else []
        identity = json.dumps([owner, accepted_repository["full_name"], accepted_repository["frozenCommitSha"],
                               kind, row["candidateID"], uids], ensure_ascii=True, separators=(",", ":"))
        record: dict[str, Any] = {"kind": kind, "candidateID": row["candidateID"], "originalCandidate": deepcopy(row),
            "sourceLocalCandidateID": "github:candidate:" + hashlib.sha256(identity.encode()).hexdigest(),
            "findings": [], "boundEvidence": [], "evidenceBindings": [], "dependencies": [],
            "semanticStatus": "not_evaluated", "kgAuthorization": False, "suppressedDuplicate": False}

        def finding(reason: str, disposition: str = "rejected_invalid_assertion", **extra: Any) -> None:
            """Keep every local reason, including simultaneous dependency failures."""
            record["findings"].append({"reason": reason, "disposition": disposition, **deepcopy(extra)})

        def resolve(ref: Any, allow_candidate: bool = True) -> dict[str, Any] | None:
            """Use exact trusted or local references; never infer Publication identity."""
            if (not isinstance(ref, Mapping) or set(ref) != {"referenceType", "referenceID"}
                    or not nonempty(ref.get("referenceID")) or not isinstance(ref.get("referenceType"), str)):
                finding("endpoint_reference_missing_or_malformed", "unresolved_endpoint")
                return None
            rid = ref["referenceID"]
            if ref["referenceType"] == "candidate_node" and allow_candidate:
                record["dependencies"].append(rid)
                parent = nodes.get(rid)
                if parent is None or parent.get("resolvedEndpoint") is None:
                    finding("candidate_endpoint_unresolved", "unresolved_endpoint", referenceID=rid)
                    return None
                if parent["disposition"] not in {"validated", "suppressed_duplicate"}:
                    finding("dependent_node_not_validated", "unresolved_endpoint", referenceID=rid,
                            parentDisposition=parent["disposition"])
                return deepcopy(parent["resolvedEndpoint"])
            if ref["referenceType"] != "accepted_endpoint":
                finding("endpoint_reference_type_invalid")
                return None
            matches = endpoints.get(rid, [])
            if len(matches) != 1 or matches[0].get("trustedEndpointValid") is False:
                finding("trusted_endpoint_missing_invalid_or_ambiguous", "unresolved_endpoint", referenceID=rid)
                return None
            return deepcopy(matches[0])

        fields = ({"candidateID", "inventoryId", "class", "label", "evidence", "endpoint"} if kind == "node"
                  else {"candidateID", "inventoryId", "relation", "source", "target", "evidence"})
        required = fields - ({"endpoint"} if kind == "node" else {"source", "target"})
        if kind == "node" and identifier == "A-C10":
            fields.add("productRepositoryID")
            required.add("productRepositoryID")
        if kind == "edge" and identifier == "C-C07":
            fields.update({"categoryKey", "classification", "reason"})
            required.add("categoryKey")
        if kind == "edge" and identifier == "C-C16":
            fields.update({"methodSurfaceForm", "candidatePublicationIdentifier"})
        if set(row) - fields or required - set(row):
            finding("candidate_fields_invalid")
        if kind == "node":
            external = resolve(row["endpoint"], False) if "endpoint" in row else None
            if not nonempty(row.get("label")):
                finding("node_label_missing_or_malformed")
            if policy is None or row.get("class") != policy["declaration"]["name"]:
                finding("class_not_allowed")
            if identifier == "A-C07":
                finding("controlled_seed_not_model_authorable")
            if identifier == "A-C10" and row.get("productRepositoryID") != owner:
                finding("model_version_not_own_repository_product")
            if external is not None and external["inventoryId"] != identifier:
                finding("node_endpoint_type_mismatch")
            exact_required = policy is not None and not policy["modelAuthorable"]
            if exact_required and external is None:
                finding("exact_endpoint_required", "unresolved_endpoint")
            checked = scope(identifier, model=external is None or identifier == "A-C07")
            record["resolvedEndpoint"] = external if external is not None else (
                {"endpointID": record["sourceLocalCandidateID"], "inventoryId": identifier, "class": row.get("class")}
                if policy is not None and policy["modelAuthorable"] and row.get("class") == policy["declaration"]["name"] else None)
            if external is not None:
                record["duplicateOf"] = [external["endpointID"]]
        else:
            source = resolve(row.get("source"))
            unresolved_category = identifier == "C-C07" and row.get("classification") in ("unclassified", "ambiguous")
            target = None if unresolved_category and row.get("target") is None else resolve(row.get("target"))
            record["resolvedSource"], record["resolvedTarget"] = source, target
            if identifier == "D-22":
                if target is not None and target["endpointID"] != owner:
                    finding("implementation_repository_owner_mismatch")
            elif source is not None and source["inventoryId"] == "A-C01" and source["endpointID"] != owner:
                finding("source_repository_owner_mismatch")
            checked = scope(identifier, relation=row.get("relation"), source=source["inventoryId"] if source else None,
                target="A-C07" if unresolved_category else target["inventoryId"] if target else None)
            if policy is None or row.get("relation") != policy["declaration"]["name"]:
                finding("relation_not_allowed")
            if identifier == "C-C16":
                finding("step14_method_resolution_not_authorized", "unresolved_endpoint")
                record["resolutionStatus"] = "unresolved_endpoint_non_KG"
        reasons = checked["reasons"]
        if reasons and not (kind == "edge" and (source is None or target is None)
                            and reasons == ["endpoint_signature_or_scope_mismatch"]):
            if not (kind == "node" and reasons == ["not_model_authorable"] and identifier in {"A-D01", "A-P13"}):
                finding("target_profile_incompatible", profileReasons=reasons)
        record["targetProfileCheck"] = {"profileResult": checked, "pendingGates": list(checked["missingGates"]),
            "targetStructuralCompatibility": policy is not None and not reasons
                and row.get("class" if kind == "node" else "relation") == policy["declaration"]["name"]
                and (kind != "node" or external is None or external["inventoryId"] == identifier)}
        if checked["missingGates"]:
            finding("semantic_gates_pending", "unresolved_condition", gates=checked["missingGates"])
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
                quote = {k: fragment[k] for k in ("evidenceText", "locatorAnchor") if k in fragment}
                binding = bind_repository_evidence(reader_result, uid, [quote], accepted_repository=accepted_repository)
                record["evidenceBindings"].append({"fragmentIndex": index, "originalFragment": deepcopy(fragment), "binding": binding})
                if binding["status"] != "evidence_bound":
                    for diagnostic in binding["diagnostics"]:
                        finding(diagnostic["reason"], binding["status"], fragmentIndex=index, bindingDiagnostic=diagnostic)
                    if binding["status"] == "needs_review" or any(d["reason"] != "evidence_quote_unbound" for d in binding["diagnostics"]):
                        result["inputComplete"] = False
                    continue
                record["boundEvidence"].extend({**deepcopy(s), "fragmentIndex": index} for s in binding["evidenceSpans"])
                if kind == "edge" and identifier == "C-C07":
                    # The binder has already proved every retained warning is unrelated
                    # to this unit. Keep originals; delegate with a scoped diagnostic view.
                    projection = {**reader_result, "diagnostics": []}
                    raw_target = row.get("target")
                    target_id = raw_target.get("referenceID") if isinstance(raw_target, Mapping) else None
                    legacy = {"candidateID": row["candidateID"], "sourceID": source["endpointID"] if source else None,
                        "sourceUnitID": uid, "inventoryId": identifier, "relation": row.get("relation"),
                        "categoryKey": row.get("categoryKey"), "targetID": target_id, "evidence": [quote],
                        **{k: row[k] for k in ("classification", "reason") if k in row}}
                    delegated = validate_purpose_candidates(projection, uid, [legacy], accepted_repository=accepted_repository)
                    record.setdefault("purposeChecks", []).append({"fragmentIndex": index, "result": delegated,
                        "diagnosticProjection": "only after scoped source/evidence verification"})
                    for diagnostic in delegated["diagnostics"]:
                        finding(diagnostic["reason"], diagnostic.get("status", "rejected_invalid_assertion"), fragmentIndex=index)
        states = {f["disposition"] for f in record["findings"]}
        record["disposition"] = next((s for s in ("failed_source_or_evidence_binding", "rejected_invalid_assertion", "needs_review",
            "unresolved_endpoint", "unresolved_category", "unresolved_condition") if s in states), "validated")
        record["validationDisposition"] = record["disposition"]
        # A later-stage Method hold does not hide an exact accepted duplicate.
        # It remains unresolved; duplicate detection cannot authorize resolution.
        duplicate_eligible = all(f["disposition"] == "unresolved_condition"
            or f["reason"] == "step14_method_resolution_not_authorized" for f in record["findings"])
        if kind == "edge" and source is not None and target is not None and duplicate_eligible:
            key = identifier, source["endpointID"], target["endpointID"]
            duplicates = accepted_keys.get(key, []) or ([seen[key]] if key in seen else [])
            if duplicates:
                record["duplicateOf"] = list(duplicates)
            else:
                seen[key] = row["candidateID"]
        if record.get("duplicateOf") and duplicate_eligible:
            record["suppressedDuplicate"] = True
            if record["disposition"] == "validated":
                record["disposition"] = "suppressed_duplicate"
        return record

    for row in payload["candidateNodes"]:
        record = check("node", row)
        nodes[row["candidateID"]] = record
        result["candidateChecks"].append(record)
    for row in payload["candidateEdges"]:
        result["candidateChecks"].append(check("edge", row))
    for record in result["candidateChecks"]:
        result["diagnostics"].extend({"candidateID": record["candidateID"], **deepcopy(f)} for f in record["findings"])
    result["status"] = "candidate_checks_completed"
    return result
