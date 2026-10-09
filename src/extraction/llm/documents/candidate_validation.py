"""Bounded Hub Procedure/C-DC20 structural and literal checks, Step 11 v0.3.

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
