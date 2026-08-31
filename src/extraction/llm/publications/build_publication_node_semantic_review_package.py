"""Build the offline M2-C2B Publication node semantic-review package.

The package reorganizes all 254 immutable C1B candidate nodes for researcher
review.  It joins authentic validator/usable status and separately labelled C2A
counterfactual diagnostics without adjudicating, modifying, or reclassifying any
candidate.  No provider, network, gold, or formal-evaluation path exists here.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from copy import deepcopy
import json
from pathlib import Path
import re
import sys
from typing import Any, Iterable, Mapping, Sequence

PROJECT_ROOT = Path(__file__).resolve().parents[4]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.extraction.llm.publications.request_builder import (  # noqa: E402
    ONTOLOGY_SPEC_PATH,
    TARGET_INVENTORY_PATH,
    canonical_json,
    canonical_json_file,
    load_json_object,
    load_yaml_object,
    sha256_bytes,
)
from src.extraction.llm.publications.run_publication_full_devset0_node_development import (  # noqa: E402
    DEV_IDS,
    load_c0_bindings,
)
from src.extraction.llm.publications.run_publication_trusted_evidence_metadata_binding import (  # noqa: E402
    C1B_OUTPUT_DIR,
    DEFAULT_OUTPUT_DIR as C2A_OUTPUT_DIR,
    _c1b_paths,
    _tree_snapshot,
)


DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "data/curation/papers/m2/c2b"
STATUS = "researcher_semantic_review_pending"
C2A_DIAGNOSTIC_PATH = (
    C2A_OUTPUT_DIR / "c1b_section_title_counterfactual_diagnostics.json"
)
MANY_CANDIDATES_THRESHOLD = 5
LONG_DISCOURSE_LABEL_CODEPOINT_THRESHOLD = 200
VERY_SHORT_DOMAIN_LABEL_CODEPOINT_THRESHOLD = 12
TOKEN_PATTERN = re.compile(r"\w+", re.UNICODE)
FLAG_ORDER = {
    name: index
    for index, name in enumerate(
        (
            "MULTI_CLASS_EVIDENCE",
            "MANY_CANDIDATES_SAME_TARGET_SAME_UNIT",
            "IDENTICAL_LABEL_DIFFERENT_TARGET",
            "IDENTICAL_LABEL_MULTIPLE_EVIDENCE",
            "LONG_DISCOURSE_LABEL",
            "VERY_SHORT_DOMAIN_LABEL",
            "AUTHENTIC_REJECTED_SECTION_TITLE_ONLY",
            "AUTHENTIC_REJECTED_RESIDUAL_EVIDENCE",
        )
    )
}


def _write_canonical(path: Path, value: Mapping[str, Any]) -> None:
    """Write one canonical JSON artifact with a trailing line feed."""

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical_json_file(value))


def _with_content_hash(value: Mapping[str, Any]) -> dict[str, Any]:
    """Attach a hash of the canonical record before its self-hash field."""

    result = deepcopy(dict(value))
    result.pop("canonicalContentSha256", None)
    result["canonicalContentSha256"] = sha256_bytes(canonical_json(result))
    return result


def evidence_occurrence_key(
    development_id: str, source_unit_id: str, evidence: Mapping[str, Any]
) -> tuple[Any, ...]:
    """Identify evidence by trusted source identity and exact position, never text alone."""

    return (
        development_id,
        source_unit_id,
        evidence.get("evidenceSpanID"),
        evidence.get("startOffsetInUnit"),
        evidence.get("endOffsetInUnit"),
        evidence.get("startOffsetInDocument"),
        evidence.get("endOffsetInDocument"),
    )


def _c2a_validation_path(development_id: str) -> Path:
    """Return one accepted C2A diagnostic validation wrapper path."""

    prefix = f"publication_m2c2a_{development_id.lower().replace('-', '')}"
    return (
        C2A_OUTPUT_DIR
        / "counterfactual"
        / development_id
        / f"{prefix}_section_title_only_validation_results.json"
    )


def _provenance() -> dict[str, Any]:
    """Bind the package to immutable C1B, C2A, target, and ontology authorities."""

    c1b = _tree_snapshot(C1B_OUTPUT_DIR)
    return {
        "c1bTreeFileCount": c1b["fileCount"],
        "c1bTreeSha256": c1b["treeInventorySha256"],
        "c2aDiagnosticArtifact": str(C2A_DIAGNOSTIC_PATH.relative_to(PROJECT_ROOT)),
        "c2aDiagnosticSha256": sha256_bytes(C2A_DIAGNOSTIC_PATH.read_bytes()),
        "targetInventorySha256": sha256_bytes(TARGET_INVENTORY_PATH.read_bytes()),
        "ontologySha256": sha256_bytes(ONTOLOGY_SPEC_PATH.read_bytes()),
        "sourceScope": "preserved M2-C1B and M2-C2A project artifacts only",
        "providerCalls": 0,
        "externalDataUsed": False,
    }


def _base_artifact(role: str, provenance: Mapping[str, Any]) -> dict[str, Any]:
    """Return common review-package metadata and non-evaluation labels."""

    return {
        "recordSchemaVersion": "0.1.0",
        "artifactRole": role,
        "status": STATUS,
        "developmentOnly": True,
        "counterfactualStatusIsDiagnosticOnly": True,
        "notGold": True,
        "notFormalEvaluation": True,
        "semanticJudgmentsMade": False,
        "candidateContentModified": False,
        "provenance": deepcopy(dict(provenance)),
    }


def _finding_codes(
    record: Mapping[str, Any],
    evidence_ids: Iterable[str],
    evidence_results: Mapping[str, Mapping[str, Any]],
) -> list[str]:
    """Return candidate and referenced-evidence finding codes without interpretation."""

    codes = {
        str(finding["code"])
        for finding in record.get("findings", [])
        if finding.get("code")
    }
    for evidence_id in evidence_ids:
        for finding in evidence_results[evidence_id].get("findings", []):
            if finding.get("code"):
                codes.add(str(finding["code"]))
    return sorted(codes)


def _load_unit(development_id: str) -> dict[str, Any]:
    """Load and join one unit's immutable authentic and diagnostic records."""

    paths = _c1b_paths(development_id)
    request = load_json_object(paths["request"])
    raw_bytes = paths["raw"].read_bytes()
    payload = json.loads(raw_bytes.decode("utf-8"))
    authentic_validation = load_json_object(paths["validation"])
    authentic_usable = load_json_object(paths["usable"])
    diagnostic_wrapper = load_json_object(_c2a_validation_path(development_id))
    if diagnostic_wrapper.get("artifactRole") != "COUNTERFACTUAL_DIAGNOSTIC_ONLY":
        raise ValueError(f"{development_id} C2A validation is not diagnostic-only")
    if diagnostic_wrapper.get("authenticModelOutput") is not False:
        raise ValueError(f"{development_id} C2A status is mislabeled authentic")
    counterfactual_validation = diagnostic_wrapper["validationResults"]
    if payload.get("candidateEdges"):
        raise ValueError(f"{development_id} C1B unexpectedly contains relation candidates")
    return {
        "request": request,
        "payload": payload,
        "rawSha256": sha256_bytes(raw_bytes),
        "authenticValidation": authentic_validation,
        "authenticUsable": authentic_usable,
        "counterfactualValidation": counterfactual_validation,
    }


def _result_index(
    validation: Mapping[str, Any], result_type: str
) -> dict[str, Mapping[str, Any]]:
    """Index validator results by their stable record identifier."""

    if result_type == "evidence":
        rows = validation.get("evidenceResults", [])
        key = "evidenceSpanID"
    else:
        rows = [
            row
            for row in validation.get("recordResults", [])
            if row.get("recordType") == result_type
        ]
        key = "recordID"
    indexed = {str(row[key]): row for row in rows}
    if len(indexed) != len(rows):
        raise ValueError(f"duplicate {result_type} validator result identifier")
    return indexed


def _target_index(units: Mapping[str, Mapping[str, Any]]) -> dict[str, Mapping[str, Any]]:
    """Verify and index the common 40-target authority embedded in every request."""

    first = list(units[DEV_IDS[0]]["request"]["targetDefinitions"])
    first_ids = [str(row["operational_id"]) for row in first]
    if len(first_ids) != 40 or len(set(first_ids)) != 40:
        raise ValueError("C1B review authority is not exactly 40 unique node targets")
    for development_id in DEV_IDS[1:]:
        rows = units[development_id]["request"]["targetDefinitions"]
        if canonical_json(rows) != canonical_json(first):
            raise ValueError(f"{development_id} target definitions differ")
    return {str(row["operational_id"]): row for row in first}


def build_candidate_rows(
    units: Mapping[str, Mapping[str, Any]],
    targets: Mapping[str, Mapping[str, Any]],
) -> list[dict[str, Any]]:
    """Build one canonical review row for each authentic C1B node candidate."""

    rows: list[dict[str, Any]] = []
    for development_id in DEV_IDS:
        unit = units[development_id]
        request = unit["request"]
        payload = unit["payload"]
        evidence = {
            str(row["evidenceSpanID"]): row for row in payload["evidenceSpans"]
        }
        authentic_evidence = _result_index(
            unit["authenticValidation"], "evidence"
        )
        counterfactual_evidence = _result_index(
            unit["counterfactualValidation"], "evidence"
        )
        authentic_candidates = _result_index(
            unit["authenticValidation"], "candidate_node"
        )
        counterfactual_candidates = _result_index(
            unit["counterfactualValidation"], "candidate_node"
        )
        authentic_usable_ids = {
            str(row["candidateID"])
            for row in unit["authenticUsable"].get("candidateNodes", [])
        }
        for index, candidate in enumerate(payload["candidateNodes"]):
            candidate_id = str(candidate["candidateID"])
            target_id = str(candidate["operationalTargetID"])
            evidence_ids = [str(value) for value in candidate["evidenceSpanIDs"]]
            if target_id not in targets:
                raise ValueError(f"unauthorized target in {development_id}:{candidate_id}")
            if any(value not in evidence for value in evidence_ids):
                raise ValueError(f"unresolved evidence in {development_id}:{candidate_id}")
            authentic_result = authentic_candidates[candidate_id]
            counterfactual_result = counterfactual_candidates[candidate_id]
            evidence_rows = []
            for evidence_id in evidence_ids:
                span = evidence[evidence_id]
                evidence_rows.append(
                    {
                        "evidenceSpanID": evidence_id,
                        "evidenceText": span["evidenceText"],
                        "startOffsetInUnit": span["startOffsetInUnit"],
                        "endOffsetInUnit": span["endOffsetInUnit"],
                        "startOffsetInDocument": span["startOffsetInDocument"],
                        "endOffsetInDocument": span["endOffsetInDocument"],
                        "authoritativeSectionTitleRaw": request["sourceUnit"][
                            "sectionTitleRaw"
                        ],
                        "modelAuthoredSectionTitle": span["sectionTitle"],
                    }
                )
            target = targets[target_id]
            authentic_status = str(
                authentic_result["candidateValidationStatus"]
            )
            counterfactual_status = str(
                counterfactual_result["candidateValidationStatus"]
            )
            rows.append(
                {
                    "reviewCandidateKey": f"{development_id}:{candidate_id}",
                    "developmentID": development_id,
                    "sourceUnitID": request["sourceUnit"]["sourceUnitID"],
                    "sourceArtifactID": request["sourceArtifactID"],
                    "sectionRole": request["sourceUnit"]["sectionRole"],
                    "candidateID": candidate_id,
                    "operationalTargetID": target_id,
                    "ontologyClassID": candidate["ontologyClassID"],
                    "className": candidate["className"],
                    "targetInventoryTreatment": target["pilot_treatment"],
                    "emissionMode": target["emission_mode"],
                    "label": candidate["label"],
                    "normalizedLabelProposal": candidate["normalizedLabelProposal"],
                    "action": candidate["action"],
                    "identityScope": candidate["identityScope"],
                    "artifactScope": candidate["artifactScope"],
                    "provisionalIdentity": candidate["provisionalIdentity"],
                    "attributes": deepcopy(candidate["attributes"]),
                    "evidenceSpanIDs": evidence_ids,
                    "evidence": evidence_rows,
                    "authenticEvidenceValid": bool(evidence_ids)
                    and all(authentic_evidence[value]["valid"] is True for value in evidence_ids),
                    "authenticCandidateValidationStatus": authentic_status,
                    "authenticValidationFindingCodes": _finding_codes(
                        authentic_result, evidence_ids, authentic_evidence
                    ),
                    "authenticUsable": candidate_id in authentic_usable_ids,
                    "sectionTitleOnlyCounterfactualApplied": True,
                    "counterfactualChangedReferencedSectionTitle": any(
                        evidence[value]["sectionTitle"]
                        != request["sourceUnit"]["sectionTitleRaw"]
                        for value in evidence_ids
                    ),
                    "counterfactualEvidenceValid": bool(evidence_ids)
                    and all(
                        counterfactual_evidence[value]["valid"] is True
                        for value in evidence_ids
                    ),
                    "counterfactualCandidateValidationStatus": counterfactual_status,
                    "counterfactualFindingCodes": _finding_codes(
                        counterfactual_result, evidence_ids, counterfactual_evidence
                    ),
                    "counterfactualHypotheticallyUsable": counterfactual_status
                    == "validated",
                    "counterfactualStatusIsDiagnosticOnly": True,
                    "notGold": True,
                    "notFormalEvaluation": True,
                    "authenticRawModelOutputSha256": unit["rawSha256"],
                    "authenticCandidateJSONPointer": f"/candidateNodes/{index}",
                    "authenticModelAuthoredCandidate": deepcopy(candidate),
                }
            )
    if len(rows) != 254:
        raise ValueError(f"expected 254 authentic candidates, found {len(rows)}")
    keys = [row["reviewCandidateKey"] for row in rows]
    if len(keys) != len(set(keys)):
        raise ValueError("candidate review keys are not unique")
    return rows


def build_evidence_groups(
    units: Mapping[str, Mapping[str, Any]], candidate_rows: Sequence[Mapping[str, Any]]
) -> list[dict[str, Any]]:
    """Group candidates by exact source-bound evidence occurrence."""

    candidate_by_unit_evidence: dict[tuple[str, str], list[Mapping[str, Any]]] = defaultdict(list)
    for candidate in candidate_rows:
        for evidence_id in candidate["evidenceSpanIDs"]:
            candidate_by_unit_evidence[
                (str(candidate["developmentID"]), str(evidence_id))
            ].append(candidate)
    pending: list[dict[str, Any]] = []
    for development_id in DEV_IDS:
        unit = units[development_id]
        request = unit["request"]
        authentic_evidence = _result_index(
            unit["authenticValidation"], "evidence"
        )
        counterfactual_evidence = _result_index(
            unit["counterfactualValidation"], "evidence"
        )
        for span in unit["payload"]["evidenceSpans"]:
            evidence_id = str(span["evidenceSpanID"])
            candidates = candidate_by_unit_evidence.get(
                (development_id, evidence_id), []
            )
            classes = sorted({str(row["className"]) for row in candidates})
            targets = sorted(
                {str(row["operationalTargetID"]) for row in candidates}
            )
            pending.append(
                {
                    "developmentID": development_id,
                    "sourceUnitID": request["sourceUnit"]["sourceUnitID"],
                    "sourceArtifactID": request["sourceArtifactID"],
                    "sectionRole": request["sourceUnit"]["sectionRole"],
                    "authoritativeSectionTitleRaw": request["sourceUnit"][
                        "sectionTitleRaw"
                    ],
                    "evidenceSpanID": evidence_id,
                    "evidenceOccurrenceKey": list(
                        evidence_occurrence_key(
                            development_id,
                            request["sourceUnit"]["sourceUnitID"],
                            span,
                        )
                    ),
                    "evidenceText": span["evidenceText"],
                    "startOffsetInUnit": span["startOffsetInUnit"],
                    "endOffsetInUnit": span["endOffsetInUnit"],
                    "startOffsetInDocument": span["startOffsetInDocument"],
                    "endOffsetInDocument": span["endOffsetInDocument"],
                    "modelAuthoredSectionTitle": span["sectionTitle"],
                    "authenticEvidenceValid": authentic_evidence[evidence_id][
                        "valid"
                    ]
                    is True,
                    "counterfactualEvidenceValid": counterfactual_evidence[
                        evidence_id
                    ]["valid"]
                    is True,
                    "counterfactualStatusIsDiagnosticOnly": True,
                    "candidateIDs": sorted(
                        str(row["candidateID"]) for row in candidates
                    ),
                    "candidateKeys": sorted(
                        str(row["reviewCandidateKey"]) for row in candidates
                    ),
                    "operationalTargetIDs": targets,
                    "ontologyClasses": classes,
                    "candidateCount": len(candidates),
                    "distinctTargetClassCount": len(classes),
                    "structuralClassMultiplicity": (
                        "multi_class" if len(classes) >= 2 else "single_class"
                        if len(classes) == 1 else None
                    ),
                }
            )
    pending.sort(
        key=lambda row: (
            row["developmentID"],
            row["sourceUnitID"],
            row["startOffsetInUnit"],
            row["endOffsetInUnit"],
            row["evidenceSpanID"],
        )
    )
    for index, row in enumerate(pending, start=1):
        row["reviewGroupID"] = f"C2B-EVID-{index:04d}"
    keys = [tuple(row["evidenceOccurrenceKey"]) for row in pending]
    if len(keys) != len(set(keys)):
        raise ValueError("evidence occurrence grouping produced a duplicate key")
    return pending


def build_multiclass_groups(
    evidence_groups: Sequence[Mapping[str, Any]],
    candidate_rows: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    """Build the deterministic evidence groups spanning two or more ontology classes."""

    candidates = {str(row["reviewCandidateKey"]): row for row in candidate_rows}
    rows: list[dict[str, Any]] = []
    for group in evidence_groups:
        if group["distinctTargetClassCount"] < 2:
            continue
        assignments = []
        for key in group["candidateKeys"]:
            candidate = candidates[key]
            assignments.append(
                {
                    "candidateID": candidate["candidateID"],
                    "candidateKey": key,
                    "operationalTargetID": candidate["operationalTargetID"],
                    "ontologyClassID": candidate["ontologyClassID"],
                    "className": candidate["className"],
                    "label": candidate["label"],
                    "attributes": deepcopy(candidate["attributes"]),
                    "authenticCandidateValidationStatus": candidate[
                        "authenticCandidateValidationStatus"
                    ],
                    "counterfactualCandidateValidationStatus": candidate[
                        "counterfactualCandidateValidationStatus"
                    ],
                    "counterfactualStatusIsDiagnosticOnly": True,
                }
            )
        rows.append(
            {
                "reviewGroupID": group["reviewGroupID"],
                "structuralClassification": "multi_class",
                "developmentID": group["developmentID"],
                "sourceUnitID": group["sourceUnitID"],
                "evidenceSpanID": group["evidenceSpanID"],
                "evidenceText": group["evidenceText"],
                "startOffsetInUnit": group["startOffsetInUnit"],
                "endOffsetInUnit": group["endOffsetInUnit"],
                "targetClassCombination": [
                    {
                        "operationalTargetID": target,
                        "classNames": sorted(
                            {
                                row["className"]
                                for row in assignments
                                if row["operationalTargetID"] == target
                            }
                        ),
                    }
                    for target in group["operationalTargetIDs"]
                ],
                "candidateIDs": group["candidateIDs"],
                "assignments": assignments,
                "authenticEvidenceValid": group["authenticEvidenceValid"],
                "counterfactualEvidenceValid": group[
                    "counterfactualEvidenceValid"
                ],
                "counterfactualStatusIsDiagnosticOnly": True,
            }
        )
    return rows


def build_target_rows(
    targets: Mapping[str, Mapping[str, Any]],
    candidate_rows: Sequence[Mapping[str, Any]],
    evidence_groups: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    """Build the complete 40-target review view, including zero-candidate targets."""

    group_by_candidate: dict[str, set[str]] = defaultdict(set)
    for group in evidence_groups:
        for key in group["candidateKeys"]:
            group_by_candidate[key].add(str(group["reviewGroupID"]))
    rows = []
    for target_id in sorted(targets):
        target = targets[target_id]
        candidates = [
            row for row in candidate_rows if row["operationalTargetID"] == target_id
        ]
        group_ids = {
            group_id
            for row in candidates
            for group_id in group_by_candidate[row["reviewCandidateKey"]]
        }
        rows.append(
            {
                "operationalTargetID": target_id,
                "ontologyClasses": [
                    {"ontologyClassID": row["id"], "className": row["name"]}
                    for row in target["formal_classes"]
                ],
                "targetInventoryTreatment": target["pilot_treatment"],
                "emissionMode": target["emission_mode"],
                "totalAuthenticCandidates": len(candidates),
                "developmentIDs": sorted(
                    {str(row["developmentID"]) for row in candidates}
                ),
                "uniqueEvidenceSpanCount": len(group_ids),
                "authenticUsableCandidateCount": sum(
                    row["authenticUsable"] is True for row in candidates
                ),
                "counterfactualHypotheticallyUsableCandidateCount": sum(
                    row["counterfactualHypotheticallyUsable"] is True
                    for row in candidates
                ),
                "labels": sorted({str(row["label"]) for row in candidates}),
                "sourceUnitIDs": sorted(
                    {str(row["sourceUnitID"]) for row in candidates}
                ),
                "sectionRoles": sorted(
                    {str(row["sectionRole"]) for row in candidates}
                ),
            }
        )
    return rows


def build_review_flags(
    candidate_rows: Sequence[Mapping[str, Any]],
    evidence_groups: Sequence[Mapping[str, Any]],
    accepted_discourse_classes: set[str],
) -> list[dict[str, Any]]:
    """Create deterministic descriptive navigation signals without semantic judgment."""

    flags: list[dict[str, Any]] = []
    group_ids_by_candidate: dict[str, set[str]] = defaultdict(set)
    for group in evidence_groups:
        for key in group["candidateKeys"]:
            group_ids_by_candidate[str(key)].add(str(group["reviewGroupID"]))
        if group["distinctTargetClassCount"] >= 2:
            flags.append(
                {
                    "flagType": "MULTI_CLASS_EVIDENCE",
                    "reviewGroupIDs": [group["reviewGroupID"]],
                    "candidateKeys": group["candidateKeys"],
                    "details": {
                        "distinctTargetClassCount": group[
                            "distinctTargetClassCount"
                        ],
                        "ontologyClasses": group["ontologyClasses"],
                    },
                }
            )

    by_unit_target: dict[tuple[str, str], list[Mapping[str, Any]]] = defaultdict(list)
    by_label: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for row in candidate_rows:
        by_unit_target[
            (str(row["developmentID"]), str(row["operationalTargetID"]))
        ].append(row)
        by_label[str(row["label"])].append(row)
    for (development_id, target_id), rows in sorted(by_unit_target.items()):
        if len(rows) >= MANY_CANDIDATES_THRESHOLD:
            flags.append(
                {
                    "flagType": "MANY_CANDIDATES_SAME_TARGET_SAME_UNIT",
                    "reviewGroupIDs": sorted(
                        {
                            group_id
                            for row in rows
                            for group_id in group_ids_by_candidate[
                                row["reviewCandidateKey"]
                            ]
                        }
                    ),
                    "candidateKeys": sorted(
                        str(row["reviewCandidateKey"]) for row in rows
                    ),
                    "details": {
                        "developmentID": development_id,
                        "operationalTargetID": target_id,
                        "candidateCount": len(rows),
                        "thresholdInclusive": MANY_CANDIDATES_THRESHOLD,
                    },
                }
            )
    for label, rows in sorted(by_label.items()):
        targets = sorted({str(row["operationalTargetID"]) for row in rows})
        group_ids = sorted(
            {
                group_id
                for row in rows
                for group_id in group_ids_by_candidate[row["reviewCandidateKey"]]
            }
        )
        keys = sorted(str(row["reviewCandidateKey"]) for row in rows)
        if len(targets) >= 2:
            flags.append(
                {
                    "flagType": "IDENTICAL_LABEL_DIFFERENT_TARGET",
                    "reviewGroupIDs": group_ids,
                    "candidateKeys": keys,
                    "details": {"exactLabel": label, "operationalTargetIDs": targets},
                }
            )
        if len(group_ids) >= 2:
            flags.append(
                {
                    "flagType": "IDENTICAL_LABEL_MULTIPLE_EVIDENCE",
                    "reviewGroupIDs": group_ids,
                    "candidateKeys": keys,
                    "details": {"exactLabel": label, "evidenceOccurrenceCount": len(group_ids)},
                }
            )
    for row in candidate_rows:
        key = str(row["reviewCandidateKey"])
        group_ids = sorted(group_ids_by_candidate[key])
        label = str(row["label"])
        if (
            row["className"] in accepted_discourse_classes
            and len(label) > LONG_DISCOURSE_LABEL_CODEPOINT_THRESHOLD
        ):
            flags.append(
                {
                    "flagType": "LONG_DISCOURSE_LABEL",
                    "reviewGroupIDs": group_ids,
                    "candidateKeys": [key],
                    "details": {
                        "labelCodePointLength": len(label),
                        "thresholdExclusive": LONG_DISCOURSE_LABEL_CODEPOINT_THRESHOLD,
                    },
                }
            )
        token_count = len(TOKEN_PATTERN.findall(label))
        if row["className"] not in accepted_discourse_classes and (
            token_count == 1
            or len(label) <= VERY_SHORT_DOMAIN_LABEL_CODEPOINT_THRESHOLD
        ):
            flags.append(
                {
                    "flagType": "VERY_SHORT_DOMAIN_LABEL",
                    "reviewGroupIDs": group_ids,
                    "candidateKeys": [key],
                    "details": {
                        "labelCodePointLength": len(label),
                        "tokenCount": token_count,
                        "oneTokenOrAtMostCodePoints": VERY_SHORT_DOMAIN_LABEL_CODEPOINT_THRESHOLD,
                    },
                }
            )
        if (
            row["authenticCandidateValidationStatus"] == "rejected"
            and row["counterfactualCandidateValidationStatus"] == "validated"
        ):
            flags.append(
                {
                    "flagType": "AUTHENTIC_REJECTED_SECTION_TITLE_ONLY",
                    "reviewGroupIDs": group_ids,
                    "candidateKeys": [key],
                    "details": {
                        "authenticFindingCodes": row[
                            "authenticValidationFindingCodes"
                        ],
                        "counterfactualFindingCodes": row[
                            "counterfactualFindingCodes"
                        ],
                        "counterfactualStatusIsDiagnosticOnly": True,
                    },
                }
            )
        if (
            row["authenticCandidateValidationStatus"] == "rejected"
            and row["counterfactualCandidateValidationStatus"] == "rejected"
        ):
            flags.append(
                {
                    "flagType": "AUTHENTIC_REJECTED_RESIDUAL_EVIDENCE",
                    "reviewGroupIDs": group_ids,
                    "candidateKeys": [key],
                    "details": {
                        "authenticFindingCodes": row[
                            "authenticValidationFindingCodes"
                        ],
                        "counterfactualFindingCodes": row[
                            "counterfactualFindingCodes"
                        ],
                        "counterfactualStatusIsDiagnosticOnly": True,
                    },
                }
            )
    flags.sort(
        key=lambda row: (
            FLAG_ORDER[row["flagType"]],
            row["reviewGroupIDs"],
            row["candidateKeys"],
            canonical_json(row["details"]),
        )
    )
    for index, row in enumerate(flags, start=1):
        row["reviewFlagID"] = f"C2B-FLAG-{index:04d}"
        row["descriptiveNavigationAidOnly"] = True
        row["semanticErrorAsserted"] = False
    return flags


def build_summary(
    candidate_rows: Sequence[Mapping[str, Any]],
    evidence_groups: Sequence[Mapping[str, Any]],
    target_rows: Sequence[Mapping[str, Any]],
    flags: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Compute descriptive review statistics without accuracy metrics."""

    by_unit = Counter(str(row["developmentID"]) for row in candidate_rows)
    by_role = Counter(str(row["sectionRole"]) for row in candidate_rows)
    class_distribution = Counter(
        int(row["distinctTargetClassCount"]) for row in evidence_groups
    )
    single_candidate = sum(row["candidateCount"] == 1 for row in evidence_groups)
    multiple_candidate = sum(row["candidateCount"] >= 2 for row in evidence_groups)
    label_targets: dict[str, set[str]] = defaultdict(set)
    label_groups: dict[str, set[tuple[Any, ...]]] = defaultdict(set)
    group_key_by_unit_evidence = {
        (row["developmentID"], row["evidenceSpanID"]): tuple(
            row["evidenceOccurrenceKey"]
        )
        for row in evidence_groups
    }
    for row in candidate_rows:
        label = str(row["label"])
        label_targets[label].add(str(row["operationalTargetID"]))
        for evidence_id in row["evidenceSpanIDs"]:
            label_groups[label].add(
                group_key_by_unit_evidence[(row["developmentID"], evidence_id)]
            )
    return {
        "totalAuthenticCandidates": len(candidate_rows),
        "candidateCountByTarget": {
            row["operationalTargetID"]: row["totalAuthenticCandidates"]
            for row in target_rows
        },
        "candidateCountByDevelopmentID": dict(sorted(by_unit.items())),
        "candidateCountBySectionRole": dict(sorted(by_role.items())),
        "uniqueEvidenceOccurrenceCount": len(evidence_groups),
        "zeroCandidateEvidenceGroupCount": sum(
            row["distinctTargetClassCount"] == 0 for row in evidence_groups
        ),
        "singleClassEvidenceGroupCount": sum(
            row["distinctTargetClassCount"] == 1 for row in evidence_groups
        ),
        "multiClassEvidenceGroupCount": sum(
            row["distinctTargetClassCount"] >= 2 for row in evidence_groups
        ),
        "distinctClassCountPerEvidenceDistribution": {
            str(key): value for key, value in sorted(class_distribution.items())
        },
        "exactLabelsReusedAcrossTargets": sum(
            len(values) >= 2 for values in label_targets.values()
        ),
        "exactLabelsReusedAcrossSourcePositions": sum(
            len(values) >= 2 for values in label_groups.values()
        ),
        "authenticUsableCandidateCount": sum(
            row["authenticUsable"] is True for row in candidate_rows
        ),
        "counterfactualHypotheticallyUsableCandidateCount": sum(
            row["counterfactualHypotheticallyUsable"] is True
            for row in candidate_rows
        ),
        "residualRejectedCandidateCount": sum(
            row["counterfactualCandidateValidationStatus"] == "rejected"
            for row in candidate_rows
        ),
        "reviewFlagCountByType": dict(
            sorted(Counter(str(row["flagType"]) for row in flags).items())
        ),
        "humanReviewWorkload": {
            "candidateRows": len(candidate_rows),
            "uniqueEvidenceCenteredReviewGroups": len(evidence_groups),
            "multiClassGroups": sum(
                row["distinctTargetClassCount"] >= 2 for row in evidence_groups
            ),
            "groupsContainingOnlyOneCandidate": single_candidate,
            "groupsContainingAtLeastTwoCandidates": multiple_candidate,
            "groupsContainingNoCandidate": sum(
                row["candidateCount"] == 0 for row in evidence_groups
            ),
            "maximumCandidatesInOneEvidenceGroup": max(
                (int(row["candidateCount"]) for row in evidence_groups), default=0
            ),
            "timeEstimateProvided": False,
        },
        "accuracyMetricsComputed": False,
    }


def _review_markdown(
    evidence_groups: Sequence[Mapping[str, Any]],
    candidate_rows: Sequence[Mapping[str, Any]],
    flags: Sequence[Mapping[str, Any]],
    provenance: Mapping[str, Any],
) -> str:
    """Render an evidence-centered Markdown template with only empty review fields."""

    candidate_index = {
        str(row["reviewCandidateKey"]): row for row in candidate_rows
    }
    flags_by_group: dict[str, list[str]] = defaultdict(list)
    for flag in flags:
        for group_id in flag["reviewGroupIDs"]:
            flags_by_group[str(group_id)].append(str(flag["flagType"]))
    lines = [
        "# Publication node semantic development review",
        "",
        f"Status: `{STATUS}`",
        "",
        "This package contains no semantic adjudication, gold labels, or formal evaluation. "
        "C2A status is counterfactual diagnostic evidence only and is not authentic extraction output.",
        "",
        f"C1B tree SHA-256: `{provenance['c1bTreeSha256']}`",
        "",
        f"C2A diagnostic SHA-256: `{provenance['c2aDiagnosticSha256']}`",
        "",
        f"Target inventory SHA-256: `{provenance['targetInventorySha256']}`",
        "",
    ]
    for group in evidence_groups:
        lines.extend(
            [
                f"## {group['reviewGroupID']} — {group['developmentID']}",
                "",
                f"- Source unit: `{group['sourceUnitID']}`",
                f"- Section role: `{group['sectionRole']}`",
                f"- Evidence span: `{group['evidenceSpanID']}`",
                f"- Unit offsets: `{group['startOffsetInUnit']}:{group['endOffsetInUnit']}`",
                f"- Document offsets: `{group['startOffsetInDocument']}:{group['endOffsetInDocument']}`",
                f"- Authentic evidence valid: `{str(group['authenticEvidenceValid']).lower()}`",
                f"- C2A diagnostic evidence valid: `{str(group['counterfactualEvidenceValid']).lower()}`",
                "- C2A status is diagnostic only: `true`",
                "",
                "Exact evidence text:",
                "",
                "~~~~text",
                str(group["evidenceText"]),
                "~~~~",
                "",
                "Candidates:",
                "",
            ]
        )
        if group["candidateKeys"]:
            lines.extend(
                [
                    "| Candidate | Target | Class | Label | Authentic | C2A diagnostic |",
                    "|---|---|---|---|---|---|",
                ]
            )
            for key in group["candidateKeys"]:
                row = candidate_index[str(key)]
                label = json.dumps(row["label"], ensure_ascii=False).replace("|", "\\|")
                lines.append(
                    f"| `{row['candidateID']}` | `{row['operationalTargetID']}` | "
                    f"`{row['className']}` | {label} | "
                    f"`{row['authenticCandidateValidationStatus']}` | "
                    f"`{row['counterfactualCandidateValidationStatus']}` |"
                )
        else:
            lines.append("No candidate references this authentic evidence span.")
        lines.extend(
            [
                "",
                "Descriptive review flags: "
                + (
                    ", ".join(f"`{value}`" for value in sorted(set(flags_by_group[group["reviewGroupID"]])))
                    if flags_by_group[group["reviewGroupID"]]
                    else "none"
                ),
                "",
                "Researcher semantic assessment:",
                "",
                "- [ ] Appropriate ontology assignment(s)",
                "- [ ] Potential over-classification",
                "- [ ] Potential under-classification",
                "- [ ] Wrong ontology class",
                "- [ ] Granularity concern",
                "- [ ] Candidate redundancy concern",
                "- [ ] Label concern",
                "- [ ] Other",
                "",
                "Researcher notes:",
                "",
                "",
            ]
        )
    return "\n".join(lines).rstrip() + "\n"


def generate_review_package(output_dir: Path = DEFAULT_OUTPUT_DIR) -> dict[str, Any]:
    """Generate all deterministic C2B JSON and Markdown review artifacts offline."""

    provenance = _provenance()
    units = {development_id: _load_unit(development_id) for development_id in DEV_IDS}
    targets = _target_index(units)
    candidate_rows = build_candidate_rows(units, targets)
    evidence_groups = build_evidence_groups(units, candidate_rows)
    multiclass_groups = build_multiclass_groups(evidence_groups, candidate_rows)
    target_rows = build_target_rows(targets, candidate_rows, evidence_groups)
    profile = load_yaml_object(TARGET_INVENTORY_PATH)
    accepted_discourse = set(
        profile["class_expansions"]["accepted_discourse_node"]
    )
    flags = build_review_flags(candidate_rows, evidence_groups, accepted_discourse)
    summary = build_summary(candidate_rows, evidence_groups, target_rows, flags)

    artifacts = {
        "candidates": _with_content_hash(
            {
                **_base_artifact("publication_node_semantic_review_candidates", provenance),
                "candidateCount": len(candidate_rows),
                "rows": candidate_rows,
            }
        ),
        "evidenceGroups": _with_content_hash(
            {
                **_base_artifact("publication_node_semantic_review_evidence_groups", provenance),
                "evidenceGroupCount": len(evidence_groups),
                "groupingKey": [
                    "developmentID",
                    "sourceUnitID",
                    "evidenceSpanID",
                    "startOffsetInUnit",
                    "endOffsetInUnit",
                    "startOffsetInDocument",
                    "endOffsetInDocument",
                ],
                "textAloneUsedForGrouping": False,
                "rows": evidence_groups,
            }
        ),
        "multiclassGroups": _with_content_hash(
            {
                **_base_artifact("publication_node_semantic_review_multiclass_groups", provenance),
                "structuralClassificationOnly": True,
                "semanticErrorAsserted": False,
                "groupCount": len(multiclass_groups),
                "rows": multiclass_groups,
            }
        ),
        "byTarget": _with_content_hash(
            {
                **_base_artifact("publication_node_semantic_review_by_target", provenance),
                "authorizedTargetCount": len(target_rows),
                "rows": target_rows,
            }
        ),
        "flags": _with_content_hash(
            {
                **_base_artifact("publication_node_semantic_review_flags", provenance),
                "descriptiveNavigationAidsOnly": True,
                "semanticErrorsAsserted": False,
                "thresholdsDeclaredBeforeApplication": {
                    "MANY_CANDIDATES_SAME_TARGET_SAME_UNIT": {
                        "candidateCountAtLeast": MANY_CANDIDATES_THRESHOLD
                    },
                    "LONG_DISCOURSE_LABEL": {
                        "classMembershipAuthority": "target inventory class_expansions.accepted_discourse_node",
                        "labelCodePointLengthGreaterThan": LONG_DISCOURSE_LABEL_CODEPOINT_THRESHOLD,
                    },
                    "VERY_SHORT_DOMAIN_LABEL": {
                        "domainDefinition": "class not in target inventory class_expansions.accepted_discourse_node",
                        "rule": "one Unicode-word token or no more than 12 Unicode code points",
                        "codePointThresholdInclusive": VERY_SHORT_DOMAIN_LABEL_CODEPOINT_THRESHOLD,
                    },
                },
                "flagCount": len(flags),
                "rows": flags,
            }
        ),
    }
    paths = {
        "candidates": output_dir / "publication_node_semantic_review_candidates.json",
        "evidenceGroups": output_dir / "publication_node_semantic_review_evidence_groups.json",
        "multiclassGroups": output_dir / "publication_node_semantic_review_multiclass_groups.json",
        "byTarget": output_dir / "publication_node_semantic_review_by_target.json",
        "flags": output_dir / "publication_node_semantic_review_flags.json",
        "template": output_dir / "publication_node_semantic_review_template.md",
        "summary": output_dir / "publication_node_semantic_review_summary.json",
    }
    for key in ("candidates", "evidenceGroups", "multiclassGroups", "byTarget", "flags"):
        _write_canonical(paths[key], artifacts[key])
    markdown = _review_markdown(evidence_groups, candidate_rows, flags, provenance)
    paths["template"].parent.mkdir(parents=True, exist_ok=True)
    paths["template"].write_bytes(markdown.encode("utf-8"))
    summary_artifact = _with_content_hash(
        {
            **_base_artifact("publication_node_semantic_review_summary", provenance),
            **summary,
            "artifactFileSha256": {
                key: sha256_bytes(path.read_bytes())
                for key, path in paths.items()
                if key != "summary"
            },
        }
    )
    _write_canonical(paths["summary"], summary_artifact)
    return {
        **artifacts,
        "summary": summary_artifact,
        "templateSha256": sha256_bytes(paths["template"].read_bytes()),
    }


def main(argv: Sequence[str] | None = None) -> int:
    """Run the deterministic C2B package generator without network access."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    args = parser.parse_args(argv)
    package = generate_review_package(args.output_dir)
    print(canonical_json(package["summary"]).decode("utf-8"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
