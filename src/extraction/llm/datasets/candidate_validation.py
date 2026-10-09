"""Bounded in-memory Variable/C-D16 structural and literal-evidence validation.

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
    AbstractSourceUnit, CONTRACT_ID, bind_abstract_evidence, build_abstract_source_unit,
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
