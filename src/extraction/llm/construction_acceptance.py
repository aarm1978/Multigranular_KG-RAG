"""Step 13.1 offline post-replay construction projection; no semantic validator.

Consumes sealed Step 12 replay reports only. Caller-supplied request association
must already have passed replay. Hashes link provenance, never attest a provider.
Original reports remain the authority for all diagnostics and suppressed evidence.
"""
from __future__ import annotations

from dataclasses import dataclass
import importlib
import json
from pathlib import Path
from typing import Any

from src.extraction.llm.pilot_preflight import canonical, digest
from src.extraction.llm.format_conformance import DIRECTORIES, VERSION, SCHEMA_VERSION

POLICY_ID = "study2-construction-acceptance/0.1.0"
POLICY_PATH = Path(__file__).resolve().parents[3] / "docs/study2_step13_construction_acceptance_policy_v0.1.md"
PARENT_GATES = {"accepted_procedure_or_step_parent", "accepted_required_parent_relations",
                "independent_parent_and_dependent_evidence"}
RELEASES = {
    "hydroshare": {key: {"explicit_readme_measurement"} for key in ("A-D12", "C-D17")},
    "github": {
        **{key: {"explicit_descriptive_prose"} for key in ("A-C08", "C-C08", "A-DOM13", "C-C20")},
        "C-C07": {"repository_specific_purpose_evidence", "approved_category_endpoint"},
        **{key: {"own_repository_product", "explicit_prose_version", "absent_from_deterministic_assertions"}
           for key in ("A-C10", "C-C09")},
    },
    "ciroh_hub": {
        **{key: {"supported_method", "substantive_method_description"} for key in ("A-P13", "C-DC28")},
        **{key: PARENT_GATES for key in ("A-DC08", "C-DC12")},
        **{key: PARENT_GATES | {"explanatory_parameter_prose"} for key in ("A-DOM12", "C-DC11")},
    },
}
DEPENDENCY_REASONS = {"dependent_node_not_validated", "dependent_candidate_not_validated",
                      "dependent_semantic_conditions_pending"}
ELIGIBLE = {"validated", "unresolved_condition", "unresolved_endpoint", "suppressed_duplicate"}


@dataclass(frozen=True)
class AcceptanceReport:
    """Immutable canonical decision report with a separately hashable projection."""

    report_json: str
    report_sha256: str

    def to_record(self) -> dict[str, Any]:
        """Return a detached view without exposing mutable report state."""
        return json.loads(self.report_json)


def project_replay(replay: Any, *, policy_version: str | None = None) -> AcceptanceReport:
    """Apply the approved policy to one sealed, independently associated replay.

    This is a trusted pipeline interface, not an ingestion boundary for arbitrary
    model-authored reports. It never reruns or changes validators. Hub's verified
    attachment cycles are admitted together only after all local checks pass;
    monotone removal then closes the set over every dependency and duplicate.
    New ModelVersion identities remain held: Step 12's prose label supplies no
    exact structured-version identity or complete deterministic comparison set.
    ModelVersion endpoint/assertion duplicate references are provenance only:
    the frozen contract does not bind candidate evidence to structured identity.
    """
    if digest(replay.report_json.encode()) != replay.report_sha256:
        raise ValueError("replay integrity mismatch")
    original = json.loads(replay.report_json)
    family = original["artifactFamily"]
    if family not in DIRECTORIES:
        raise ValueError("unsupported replay family")
    body = original.get("requestResult", {}).get("request", {})
    policy_id, policy_path = POLICY_ID, POLICY_PATH
    if policy_version is not None:
        from src.extraction.llm import source_local_profile as prospective
        from src.extraction.llm.semantic_target_profiles import get_profile
        if (policy_version != prospective.VERSION or body.get("contractID") != policy_version
                or body.get("targetProfile") != get_profile(family, version=policy_version)):
            raise ValueError("prospective_policy_or_profile_mismatch")
        policy_id, policy_path = prospective.VERSION, prospective.POLICY_PATH
    elif str(body.get("contractID", "")).startswith("study2-source-local-semantics/"):
        raise ValueError("explicit_prospective_acceptance_required")
    rows = {r["candidateID"]: r for r in original["finalRecords"]}
    checks = {cid: r.get("validationRecord") or {} for cid, r in rows.items()}
    owner = body.get("owner", {})
    external = {e["endpointID"]: e for e in [owner, *body.get("acceptedEndpoints", []),
                *body.get("authorizedStubs", [])] if "endpointID" in e}
    assertions = {a["assertionID"]: a for a in body.get("acceptedAssertions", [])}
    units = {u["sourceUnitID"]: u for u in body.get("sourceUnits", [])}
    selected = set(body.get("selectedSourceUnitIDs", []))
    reasons: dict[str, list[str]] = {cid: [] for cid in rows}
    dependencies = {cid: set(c.get("dependencies", [])) for cid, c in checks.items()}
    exact_duplicates: dict[str, list[str]] = {}
    global_blocks = []
    if (original.get("status") != "replay_completed"
            or original.get("parseResult", {}).get("status") != "response_parsed"
            or (original.get("validationResult") or {}).get("status") != "candidate_checks_completed"):
        global_blocks.append("response_not_processable")
    if (original.get("requestAssociation") != "matched_caller_supplied_digest"
            or not original.get("expectedRequestSha256")
            or original["expectedRequestSha256"] != original.get("requestSha256")
            or original.get("requestSha256") != original.get("requestResult", {}).get("requestSha256")):
        global_blocks.append("independent_request_association_required")
    if original.get("diagnostics"):
        global_blocks.append("replay_diagnostics_present")

    for cid, row in rows.items():
        c, blocked = checks[cid], reasons[cid]
        candidate = row["originalCandidate"]
        identifier = candidate.get("inventoryId")
        allowed = RELEASES[family].get(identifier, set())
        profile = c.get("targetProfileCheck", {})
        gates = set(profile.get("pendingGates", [])) | set(profile.get("profileResult", {}).get("missingGates", []))
        if (row.get("finalDisposition") not in ELIGIBLE or c.get("disposition") not in ELIGIBLE
                or row.get("parseDisposition") != "pending_validation" or row.get("parseDiagnostics")
                or row.get("replayDiagnostics") or not c or candidate != c.get("originalCandidate")):
            blocked.append("original_record_not_eligible")
            blocked.extend(f["reason"] for f in c.get("findings", []))
            # Quarantined original candidates may contain arbitrary malformed
            # fields. Preserve them, but never interpret them as usable records.
            continue
        if not profile.get("targetStructuralCompatibility") or profile.get("profileResult", {}).get("reasons"):
            blocked.append("original_target_incompatibility")
        if gates - allowed:
            blocked.append("nonreleasable_pending_gates")
        for finding in c.get("findings", []):
            reason = finding["reason"]
            if reason in {"semantic_gate_pending", "semantic_gates_pending"}:
                if (finding.get("disposition") != "unresolved_condition" or not finding.get("gates")
                        or set(finding["gates"]) - allowed):
                    blocked.append(reason)
            elif reason in DEPENDENCY_REASONS:
                dep = finding.get("referenceID", finding.get("dependencyID"))
                if (finding.get("disposition") not in {"unresolved_endpoint", "unresolved_condition"}
                        or not dependencies[cid] or (dep is not None and dep not in dependencies[cid])):
                    blocked.append(reason)
            elif reason == "parent_semantic_acceptance_not_evaluated":
                if (finding.get("disposition") != "unresolved_condition" or family != "ciroh_hub"
                        or c.get("parentPathStructurallyLinked") is not True):
                    blocked.append(reason)
            else:
                blocked.append(reason)
        if "parentPathStructurallyLinked" in c and c["parentPathStructurallyLinked"] is not True:
            blocked.append("parent_path_not_verified")
        for ref in candidate.get("parentPath", []):
            if ref["referenceType"] == "candidate_edge":
                dependencies[cid].add(ref["referenceID"])
            elif ref["referenceType"] != "accepted_assertion" or ref["referenceID"] not in assertions:
                blocked.append("parent_path_reference_unavailable")
        bindings = c.get("evidenceBindings", [])
        if (not c.get("boundEvidence") or len(bindings) != len(candidate.get("evidence", [])) or not bindings
                or any(b["binding"].get("status") not in {"evidence_bound", "example_context_bound"} for b in bindings)):
            blocked.append("independent_evidence_not_bound")
        for fragment in candidate.get("evidence", []):
            uid = fragment.get("sourceUnitID")
            if uid not in selected or uid not in units:
                blocked.append("evidence_source_not_selected")
            if family == "hydroshare" and identifier in {"A-D12", "C-D17"}:
                unit = units.get(uid, {})
                if unit.get("sourceField") != "README" or unit.get("sourceVerification") != "caller_attested":
                    blocked.append("verified_readme_evidence_required")
        if family == "github" and identifier in {"A-P13", "C-C16"}:
            blocked.append("step14_method_resolution_not_authorized")
        if family == "github" and identifier == "C-C07":
            from src.extraction.llm.coderepos.purpose_validation import purpose_vocabulary
            seeds = {s["categoryKey"]: s["nodeID"] for s in purpose_vocabulary()}
            endpoint = c.get("resolvedTarget") or {}
            if (candidate.get("classification") != "proposed"
                    or seeds.get(candidate.get("categoryKey")) != endpoint.get("endpointID")
                    or endpoint.get("inventoryId") != "A-C07"
                    or (c.get("resolvedSource") or {}).get("endpointID") != owner.get("endpointID")):
                blocked.append("approved_category_endpoint_required")
        if (row["kind"] == "edge" and c.get("resolvedSource") and c.get("resolvedTarget")
                and not (family == "github" and identifier == "C-C09")):
            exact_duplicates[cid] = sorted(aid for aid, a in assertions.items()
                if (a["inventoryId"], a["sourceID"], a["targetID"]) ==
                   (identifier, c["resolvedSource"]["endpointID"], c["resolvedTarget"]["endpointID"]))
        if family == "github" and identifier in {"A-C10", "C-C09"}:
            # Trusted deterministic version/toolId attributes identify the stored
            # version, not the assertion made by the candidate's bound prose.
            # The frozen candidate contract has no independently verified mapping
            # from that evidence to structured version/product identity. Matching
            # labels, quoted tokens, selected endpoint IDs or assertion triples
            # cannot supply that missing comparison (even for a direct edge to an
            # accepted endpoint). Preserve original duplicateOf/findings as
            # provenance; never promote them to construction duplicate proof.
            proof = None
            if policy_version is not None:
                from src.extraction.llm.source_local_semantics import _version_proof
                proof = _version_proof(body, candidate, c)
            if not proof or proof != c.get("versionIdentityProof"):
                blocked.append("exact_deterministic_version_comparison_unavailable")
                blocked.append("candidate_version_product_identity_not_established")
        if row["kind"] == "node":
            if not c.get("resolvedEndpoint"):
                blocked.append("endpoint_unresolved")
        else:
            for key, resolved in (("source", "resolvedSource"), ("target", "resolvedTarget")):
                ref, endpoint = candidate.get(key) or {}, c.get(resolved)
                rid = ref.get("referenceID")
                if not endpoint:
                    blocked.append("endpoint_unresolved")
                elif ref.get("referenceType") == "candidate_node":
                    dependencies[cid].add(rid)
                    if (checks.get(rid, {}).get("kind") != "node"
                            or checks.get(rid, {}).get("resolvedEndpoint") != endpoint):
                        blocked.append("local_endpoint_identity_mismatch")
                elif rid not in external or endpoint.get("endpointID") != rid:
                    blocked.append("trusted_endpoint_unavailable")
        if c.get("duplicateOf") or c.get("suppressedDuplicate"):
            if not c.get("duplicateOf") or c.get("suppressedDuplicate") is not True:
                blocked.append("duplicate_state_inconsistent")
            for duplicate in c.get("duplicateOf", []):
                if duplicate in rows:
                    dependencies[cid].add(duplicate)
                elif duplicate not in external and duplicate not in assertions:
                    blocked.append("duplicate_reference_unavailable")

    surviving = {cid for cid in rows if not reasons[cid] and not global_blocks}
    while True:
        removed = {cid for cid in surviving if dependencies[cid] - surviving}
        if not removed:
            break
        for cid in sorted(removed):
            reasons[cid].append("construction_dependency_not_admitted")
        surviving -= removed
    # Released conditional edges may not have participated in the upstream
    # validator's duplicate pass. Suppress only identical resolved assertions.
    duplicates = {cid: exact_duplicates.get(cid) or list(c.get("duplicateOf", [])) for cid, c in checks.items()}
    seen_edges: dict[tuple[str, str, str], str] = {}
    for cid in sorted(surviving):
        c = checks[cid]
        if rows[cid]["kind"] != "edge" or duplicates[cid]:
            continue
        key = (rows[cid]["originalCandidate"]["inventoryId"],
               c["resolvedSource"]["endpointID"], c["resolvedTarget"]["endpointID"])
        if key in seen_edges:
            duplicates[cid] = [seen_edges[key]]
        else:
            seen_edges[key] = cid
    projection = {"policyID": policy_id, "policySha256": digest(policy_path.read_bytes()),
        "artifactFamily": family, "owner": owner, "replaySha256": replay.report_sha256,
        "requestSha256": original.get("requestSha256"), "responseSha256": original.get("responseSha256"),
        "sourceSnapshot": original.get("sourceSnapshot"), "nodes": [], "edges": [], "externalEndpoints": [],
        "kgAuthorization": False}
    decisions = []
    used_external = set()
    for cid in sorted(rows):
        row, c = rows[cid], checks[cid]
        duplicate = bool(duplicates[cid])
        included = cid in surviving and not duplicate
        conditional = row["finalDisposition"] != "validated"
        basis = "policy_conditional_inclusion" if conditional else "policy_ordinary_inclusion"
        decisions.append({"candidateID": cid, "originalDisposition": row["finalDisposition"],
            "disposition": "accepted" if included else "suppressed_duplicate" if duplicate and cid in surviving else "held",
            "blockingReasons": sorted(set(reasons[cid] + global_blocks)),
            "acceptanceBasis": basis if included else None,
            "duplicateOf": duplicates[cid]})
        if included:
            record = {"candidateID": cid, "sourceLocalCandidateID": c["sourceLocalCandidateID"],
                "originalCandidate": row["originalCandidate"], "acceptanceBasis": basis,
                "boundEvidence": c["boundEvidence"], "dependencies": sorted(dependencies[cid]),
                "replayRecordReference": {"replaySha256": replay.report_sha256, "candidateID": cid},
                **{k: c[k] for k in ("resolvedEndpoint", "resolvedSource", "resolvedTarget") if k in c}}
            projection["nodes" if row["kind"] == "node" else "edges"].append(record)
            if row["kind"] == "edge":
                used_external.update(c[k]["endpointID"] for k in ("resolvedSource", "resolvedTarget")
                                     if c[k]["endpointID"] in external)
    projection["externalEndpoints"] = [external[e] for e in sorted(used_external)]
    report = {"schemaVersion": policy_id if policy_version else "study2-offline-construction-acceptance/0.1.0",
        "status": "processing_blocked" if global_blocks else "projection_completed",
        "blockingReasons": global_blocks, "projection": projection, "projectionSha256": digest(canonical(projection)),
        "decisions": decisions, "originalReplay": original, "originalReplaySha256": replay.report_sha256,
        "kgAuthorization": False}
    wire = canonical(report)
    return AcceptanceReport(wire.decode(), digest(wire))


def replay_and_project(recorded_response: bytes, *, family: str, request_inputs: dict,
                       expected_request_sha256: str | None,
                       conformance_version: str | None = None,
                       schema_version: str | None = None) -> AcceptanceReport:
    """Prospective OFFLINE opt-in integration; historical family defaults stay intact.

    Request digests must be independently supplied by the caller, never generated
    here as an attestation. Schema output is an unauthorized prospective artifact.
    No live transport, retry, corpus iteration or graph writer is reachable here.
    """
    if family not in DIRECTORIES:
        raise ValueError("unsupported family")
    prefix = "src.extraction.llm." + DIRECTORIES[family]
    pipeline = importlib.import_module(prefix + ".offline_pipeline")
    replay = pipeline.replay_recorded_response(recorded_response, request_inputs=request_inputs,
                                              expected_request_sha256=expected_request_sha256)
    if conformance_version is None and schema_version is None:
        return project_replay(replay)
    if conformance_version != VERSION or schema_version != SCHEMA_VERSION:
        raise ValueError("explicit supported conformance and schema versions required together")
    if expected_request_sha256 is None:
        return project_replay(replay)
    from src.extraction.llm.format_conformance import replay_conformant, build_conformant_preflight
    if json.loads(replay.report_json)["status"] != "replay_completed":
        return project_replay(replay)
    derived = replay_conformant(recorded_response, family=family, request_inputs=request_inputs,
                               expected_request_sha256=expected_request_sha256, conformance_version=conformance_version)
    # Reconstruct the existing replay serialization exactly (including ASCII
    # escapes) so its established provenance hash is not replaced by a new one.
    replay_json = json.dumps(derived["derivedReplay"], ensure_ascii=True, sort_keys=True,
                             separators=(",", ":"), allow_nan=False)
    sealed = pipeline.ReplayReport(replay_json, derived["derivedReplaySha256"],
                                   bytes.fromhex(derived["derivedResponseBytesHex"]))
    result = project_replay(sealed).to_record()
    request = json.loads(replay.report_json)["requestResult"]
    preflight = build_conformant_preflight(request, schema_version=schema_version)
    result.update(originalReplay=json.loads(replay.report_json), originalReplaySha256=replay.report_sha256,
                  conformance=derived, prospectiveSchema={k: preflight[k] for k in
                  ("responseSchemaVersion", "schemaSha256", "providerEnvelopeSha256", "authorization")})
    wire = canonical(result)
    return AcceptanceReport(wire.decode(), digest(wire))
