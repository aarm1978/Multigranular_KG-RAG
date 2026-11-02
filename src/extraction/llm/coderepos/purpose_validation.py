"""Offline Step 11 v0.3 §7 vocabulary and structural/literal purpose checks.

No semantic correctness, repository-purpose assignment or KG acceptance is
established here. All inputs are caller-supplied; no corpus/provider/graph IO.
"""

from __future__ import annotations

from copy import deepcopy
import hashlib
import json
import re
from typing import Any, Mapping, Sequence

from src.extraction.llm.publications.deterministic_evidence_binding import bind_evidence_spans
from src.extraction.llm.semantic_target_profiles import get_profile, check_target


CONTRACT = "study2-step11-semantic-contracts/v0.3"
SCHEME = "ciroh-repository-purpose"
VERSION = "1.0.0"
CATEGORIES = (
    ("model_implementation", "Model implementation", "Implements or develops a computational model as a repository purpose"),
    ("data_processing", "Data processing", "Prepares, transforms, processes, or analyzes scientific data"),
    ("scientific_experimentation", "Scientific experimentation", "Supports simulations, experiments, calibration, or evaluation as a central repository purpose"),
    ("workflow_orchestration", "Workflow orchestration", "Coordinates multi-stage scientific computation or data-processing workflows"),
    ("software_infrastructure", "Software infrastructure", "Provides a software library, interface, runtime, or reusable infrastructure"),
    ("tutorial_demonstration", "Tutorial / demonstration", "Exists principally to explain, teach, or demonstrate a technical or scientific task"),
)


def purpose_vocabulary(existing_nodes: Sequence[Mapping[str, Any]] = ()) -> list[dict[str, Any]]:
    """Return six detached seed records; check collisions only in supplied nodes.

    An identical existing seed is reusable; a different record with the same ID
    fails closed. No existing graph is read and no exhaustive collision audit is
    claimed when the caller supplies an empty inventory.
    """
    profile = get_profile("github")
    seed = profile["entities"]["A-C07"]
    scope = check_target("github", "A-C07", model_authored=False)
    if (not scope["structuralScopePass"] or seed["mode"] != "controlled_vocabulary_seed"
            or seed["modelAuthorable"] or seed["schemeID"] != SCHEME
            or seed["schemeVersion"] != VERSION or seed["categoryCount"] != len(CATEGORIES)
            or seed["nodeIDPattern"] != "repo-purpose:1.0.0:{category_key}"):
        raise ValueError("Frozen purpose vocabulary/profile inconsistency")
    records = [{"nodeID": f"repo-purpose:{VERSION}:{key}", "class": seed["declaration"]["name"],
                "inventoryId": seed["declaration"]["id"], "schemeID": SCHEME, "schemeVersion": VERSION,
                "categoryKey": key, "label": label, "definition": definition,
                "extractionMethod": "controlled_vocabulary_seed", "contractID": CONTRACT}
               for key, label, definition in CATEGORIES]
    by_id = {r["nodeID"]: r for r in records}
    for existing in existing_nodes:
        identifier = existing.get("nodeID", existing.get("id"))
        if identifier in by_id and dict(existing) != by_id[identifier]:
            raise ValueError(f"Controlled-vocabulary namespace collision: {identifier}")
    return records


def _line(text: str, offset: int) -> int:
    """Return a one-based original authority line for a Unicode offset."""
    return 1 + sum(m.end() <= offset for m in re.finditer(r"\r\n|\r|\n", text))


def validate_purpose_candidates(
    reader_result: Mapping[str, Any], source_unit_id: str, candidates: list[Any], *,
    accepted_repository: Mapping[str, Any],
) -> dict[str, Any]:
    """Check proposals against one trusted unit from the unchanged GitHub reader.

    ``accepted_repository`` independently supplies canonicalArtifactID, repo_id,
    full_name and frozenCommitSha. ``reader_result`` is a trusted pipeline input,
    never model-authored. Its matching authority, read status and diagnostics are
    checked without rereading files; computed-only hashes retain that limitation.

    Frozen profile checks read only the ontology specification. Profile reasons
    report structural incompatibility separately from pending gates; no gate is
    attested here. Existing validated dispositions still mean bounded structural
    and literal checks only, never semantic acceptance or KG authorization.

    Each proposal has candidateID, sourceID, sourceUnitID, relation, inventoryId,
    categoryKey, targetID, evidence (nonempty quote/optional locatorAnchor list).
    Optional classification is proposed, unclassified or ambiguous. The latter
    two require a reason and null categoryKey/targetID, and remain non-KG records.
    Unsupported categories are rejected, never converted to an 'other' category.
    Model-authored coordinates or other extra fields are rejected.
    """
    result: dict[str, Any] = {"vocabularyRecords": purpose_vocabulary(), "candidateChecks": [],
        "originalCandidates": deepcopy(candidates), "diagnostics": [],
        "validationScope": "structure_and_literal_evidence_only", "semanticStatus": "not_evaluated",
        "graphAcceptance": False, "kgAuthorization": False, "source": None}

    def stop(status: str, reason: str) -> dict[str, Any]:
        """Preserve technical/review failures without claiming candidate validity."""
        result["status"] = status
        result["diagnostics"].append({"status": status, "reason": reason, "sourceUnitID": source_unit_id})
        return result

    failed = "failed_source_or_evidence_binding"
    if not isinstance(reader_result, Mapping) or not isinstance(accepted_repository, Mapping):
        return stop(failed, "trusted_source_missing_or_malformed")
    for key in ("sourceUnits", "authorities", "reads", "diagnostics"):
        if not isinstance(reader_result.get(key), list):
            return stop(failed, "reader_result_malformed")
    units = [u for u in reader_result["sourceUnits"] if isinstance(u, Mapping) and u.get("sourceUnitID") == source_unit_id]
    if len(units) != 1:
        result["diagnostics"].extend(deepcopy(reader_result["diagnostics"]))
        return stop(failed, "source_unit_missing_or_ambiguous")
    unit = units[0]
    result["source"] = deepcopy(dict(unit))
    result["source"].pop("text", None)
    keys = ("canonicalArtifactID", "repo_id", "full_name", "frozenCommitSha")
    if (any(key not in accepted_repository or unit.get(key) != accepted_repository[key] for key in keys)
            or type(unit.get("repo_id")) is not int
            or unit.get("canonicalArtifactID") != f"github:repo:{unit.get('repo_id')}"
            or unit.get("artifactFamily") != "github" or unit.get("contractID") != CONTRACT):
        return stop(failed, "trusted_owner_or_provenance_mismatch")
    if unit.get("eligibility") != "prose_candidate" or unit.get("contentKind") != "prose":
        return stop("needs_review", "source_not_eligible_prose")
    def matching(row: Any) -> bool:
        """Match source-local file/cell lineage without using candidate metadata."""
        return isinstance(row, Mapping) and row.get("path") == unit.get("path") and row.get("cellIndex") == unit.get("cellIndex")
    diagnostics = [d for d in reader_result["diagnostics"] if matching(d) or isinstance(d, Mapping) and d.get("path") is None]
    result["diagnostics"].extend(deepcopy(diagnostics))
    if any(d.get("status") == failed for d in diagnostics):
        return stop(failed, "source_read_failed")
    if any(d.get("status") == "needs_review" for d in diagnostics):
        return stop("needs_review", "source_eligibility_requires_review")
    if not any(matching(r) and r.get("status") == "source_read_success" and r.get("reason") == "authority_recorded" for r in reader_result["reads"]):
        return stop(failed, "successful_source_read_missing")
    authorities = [a for a in reader_result["authorities"] if matching(a)]
    if len(authorities) != 1:
        return stop(failed, "authority_missing_or_ambiguous")
    authority = authorities[0]
    text = authority.get("text")
    if not isinstance(text, str) or any(unit.get(k) != v for k, v in authority.items() if k != "text"):
        return stop(failed, "authority_metadata_mismatch")
    try:
        digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
    except UnicodeEncodeError:
        return stop(failed, "authority_text_malformed")
    start, end = unit.get("startOffsetInAuthority"), unit.get("endOffsetInAuthority")
    if (digest != authority.get("authorityTextSha256") or type(start) is not int or type(end) is not int
            or not 0 <= start < end <= len(text) or text[start:end] != unit.get("text")):
        return stop(failed, "source_content_integrity_failure")
    identity = json.dumps([unit["repo_id"], unit["full_name"], unit["frozenCommitSha"], unit.get("path"),
                          unit.get("cellIndex"), digest, start, end], separators=(",", ":"), ensure_ascii=True)
    if (source_unit_id != "github:unit:" + hashlib.sha256(identity.encode()).hexdigest()
            or unit.get("startLine") != _line(text, start) or unit.get("endLine") != _line(text, end - 1)):
        return stop(failed, "source_unit_coordinates_or_identity_mismatch")
    if not isinstance(candidates, list):
        return stop("rejected_invalid_assertion", "candidate_list_malformed")
    profile = get_profile("github")
    relation = profile["relations"]["C-C07"]["declaration"]
    result["vocabularyProfileCheck"] = check_target("github", "A-C07", model_authored=False)
    vocabulary = {r["categoryKey"]: r["nodeID"] for r in result["vocabularyRecords"]}
    seen: dict[str, str] = {}
    ids = [c.get("candidateID") for c in candidates if isinstance(c, Mapping)]
    for candidate in candidates:
        check: dict[str, Any] = {"originalCandidate": deepcopy(candidate), "findings": [], "boundEvidence": []}
        result["candidateChecks"].append(check)

        def reject(reason: str, status: str = "rejected_invalid_assertion") -> None:
            """Append a non-repairing finding to this proposal."""
            check["findings"].append({"status": status, "reason": reason})

        if not isinstance(candidate, Mapping):
            reject("candidate_malformed")
        else:
            fields = {"candidateID", "sourceID", "sourceUnitID", "relation", "inventoryId", "categoryKey", "targetID", "evidence"}
            if fields - set(candidate) or set(candidate) - fields - {"classification", "reason"}:
                reject("candidate_fields_invalid")
            cid = candidate.get("candidateID")
            if not isinstance(cid, str) or not cid.strip() or ids.count(cid) != 1:
                reject("candidate_id_invalid_or_duplicate")
            if candidate.get("sourceID") != unit["canonicalArtifactID"] or candidate.get("sourceUnitID") != source_unit_id:
                reject("candidate_owner_or_unit_mismatch")
            if (candidate.get("relation"), candidate.get("inventoryId")) != (relation["name"], relation["id"]):
                reject("relation_not_allowed")
            mode, key = candidate.get("classification", "proposed"), candidate.get("categoryKey")
            if mode == "proposed":
                if not isinstance(key, str) or key not in vocabulary:
                    reject("category_not_allowed")
                elif candidate.get("targetID") != vocabulary[key]:
                    reject("target_binding_mismatch")
            elif mode in ("unclassified", "ambiguous"):
                if key is not None or candidate.get("targetID") is not None or not isinstance(candidate.get("reason"), str) or not candidate["reason"].strip():
                    reject("unresolved_classification_invalid")
            else:
                reject("classification_invalid")
            identifier = candidate.get("inventoryId")
            identifier = identifier if isinstance(identifier, str) else ""
            owner_bound = candidate.get("sourceID") == unit["canonicalArtifactID"]
            seed_bound = (mode == "proposed" and isinstance(key, str) and key in vocabulary
                          and candidate.get("targetID") == vocabulary[key])
            # No gate attestations: literal binding is not semantic purpose review,
            # and matching a seed ID is not external endpoint acceptance.
            scope = check_target("github", identifier,
                relation_name=candidate.get("relation"),
                source_class_id=profile["ownerClassID"] if owner_bound else None,
                target_class_id="A-C07")
            compatible = not scope["reasons"] and identifier == relation["id"]
            check["targetProfileCheck"] = {
                "artifactFamily": "github", "inventoryId": identifier,
                "profileResult": scope, "targetStructuralCompatibility": compatible,
                "ownerBound": owner_bound, "controlledSeedBound": seed_bound,
                "pendingGates": list(scope["missingGates"]),
                "semanticStatus": "not_evaluated", "kgAuthorization": False}
            if not compatible and not check["findings"]:
                reject("target_profile_incompatible")
            evidence = candidate.get("evidence")
            if (not isinstance(evidence, list) or not evidence or any(not isinstance(e, Mapping)
                    or set(e) - {"evidenceText", "locatorAnchor"} for e in evidence)):
                reject("evidence_invalid")
            else:
                bound, report = bind_evidence_spans({"evidenceSpans": evidence}, {
                    "text": unit["text"], "startOffsetInDocument": start, "canonicalArtifactID": unit["canonicalArtifactID"],
                    "sourceUnitID": source_unit_id, "textHash": hashlib.sha256(unit["text"].encode()).hexdigest(),
                    "sectionID": None, "sectionTitleRaw": unit.get("headingContext")})
                check["bindingReport"] = report
                if report["bindingStatus"] != "bound":
                    reject("evidence_quote_unbound", failed)
                else:
                    for span in bound["evidenceSpans"]:
                        lo, hi = span["startOffsetInDocument"], span["endOffsetInDocument"]
                        check["boundEvidence"].append({**deepcopy(result["source"]), "evidenceText": span["evidenceText"],
                            "startOffsetInAuthority": lo, "endOffsetInAuthority": hi,
                            "startLine": _line(text, lo), "endLine": _line(text, hi - 1)})
            if not check["findings"]:
                if mode != "proposed":
                    reject("unclassified_purpose" if mode == "unclassified" else "ambiguous_purpose", "unresolved_category")
                elif key in seen:
                    check["duplicateOf"] = seen[key]
                    reject("duplicate_equivalent_proposal")
                else:
                    seen[key] = cid
        statuses = {f["status"] for f in check["findings"]}
        check["status"] = next((s for s in (failed, "rejected_invalid_assertion", "unresolved_category") if s in statuses), "validated")
        result["diagnostics"].extend(deepcopy(check["findings"]))
    result["status"] = "candidate_checks_completed"
    return result
