"""Deterministically derive generic Publication mentions after acceptance.

The input is a neutral accepted-semantic projection, not a second candidate
schema.  Production adjudication and development-only adapters may both supply
this interface.  No parser, validation, or model-authored payload is modified.
"""

from __future__ import annotations

from copy import deepcopy
import hashlib
from pathlib import Path
from typing import Any, Mapping, Sequence

from src.extraction.llm.publications.request_builder import (
    ONTOLOGY_SPEC_PATH,
    PROJECT_ROOT,
    canonical_json,
    load_yaml_object,
    sha256_bytes,
)


POLICY_PATH = Path(__file__).with_name("generic_mentions_policy.yaml")
MATERIALIZER_VERSION = "publication-post-acceptance-generic-mentions/0.1.0"
OUTPUT_VERSION = "publication-derived-semantic-output/0.1.0"
CONTAINMENT_TERM = "EXACT_COORDINATE_CONTAINMENT"
EVIDENCE_COORDINATES = (
    "startOffsetInUnit",
    "endOffsetInUnit",
    "startOffsetInDocument",
    "endOffsetInDocument",
)


class SemanticMaterializationError(ValueError):
    """Report an invalid or ambiguous accepted-semantic projection."""


def _strings(value: Any) -> list[str]:
    """Return a scalar-or-list ontology declaration as strings."""

    return [str(item) for item in value] if isinstance(value, list) else [str(value)]


def _ontology_authority() -> tuple[dict[str, Any], dict[str, Any], set[str], set[str]]:
    """Load and reconcile D-26 and policy authority from frozen repository bytes."""

    spec = load_yaml_object(ONTOLOGY_SPEC_PATH)
    policy = load_yaml_object(POLICY_PATH)
    relations = {str(row["id"]): row for row in spec["relations"]}
    relation = relations.get(str(policy["relation"]["id"]))
    if relation is None or relation.get("name") != policy["relation"]["name"]:
        raise SemanticMaterializationError("generic mentions policy does not resolve to D-26")
    expected = policy["ontology"]
    if spec["ontology"]["version"] != expected["version"]:
        raise SemanticMaterializationError("generic mentions ontology version drift")
    if sha256_bytes(ONTOLOGY_SPEC_PATH.read_bytes()) != expected["specification_sha256"]:
        raise SemanticMaterializationError("generic mentions ontology specification drift")
    owl = PROJECT_ROOT / "src/ontology/ciroh_ontology.owl"
    if sha256_bytes(owl.read_bytes()) != expected["owl_sha256"]:
        raise SemanticMaterializationError("generic mentions OWL authority drift")
    declared_specialized = {
        str(row["name"])
        for row in spec["relations"]
        if row.get("subproperty_of") == relation["name"]
    }
    if declared_specialized != set(policy["specialized_subproperties"]):
        raise SemanticMaterializationError("D-26 specialized subproperty policy drift")
    return spec, policy, set(_strings(relation["domain"])), set(_strings(relation["range"]))


def _class_closure(spec: Mapping[str, Any], roots: set[str]) -> set[str]:
    """Expand ontology roots through declared CIROH parent relationships."""

    names = {str(row["name"]): row for row in spec["classes"]}
    result = set(roots)
    changed = True
    while changed:
        changed = False
        for name, row in names.items():
            parent = str(row.get("parent", "")).split(":")[-1]
            if parent in result and name not in result:
                result.add(name)
                changed = True
    return result


def exact_coordinate_containment(
    discourse_evidence: Mapping[str, Any], entity_evidence: Mapping[str, Any]
) -> bool:
    """Test inclusive containment in both unit and document coordinates."""

    if discourse_evidence.get("valid") is not True or entity_evidence.get("valid") is not True:
        return False
    if discourse_evidence.get("sourceUnitID") != entity_evidence.get("sourceUnitID"):
        return False
    if discourse_evidence.get("canonicalPaperID") != entity_evidence.get("canonicalPaperID"):
        return False
    try:
        return (
            int(discourse_evidence["startOffsetInUnit"])
            <= int(entity_evidence["startOffsetInUnit"])
            and int(entity_evidence["endOffsetInUnit"])
            <= int(discourse_evidence["endOffsetInUnit"])
            and int(discourse_evidence["startOffsetInDocument"])
            <= int(entity_evidence["startOffsetInDocument"])
            and int(entity_evidence["endOffsetInDocument"])
            <= int(discourse_evidence["endOffsetInDocument"])
        )
    except (KeyError, TypeError, ValueError):
        return False


def _accepted_nodes(projection: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Validate and return accepted nodes in deterministic order."""

    nodes = projection.get("acceptedNodes")
    if not isinstance(nodes, list):
        raise SemanticMaterializationError("acceptedNodes must be an array")
    result: list[dict[str, Any]] = []
    for node in nodes:
        if not isinstance(node, Mapping) or node.get("accepted") is not True:
            raise SemanticMaterializationError("every supplied node must be explicitly accepted")
        node_id = node.get("nodeID")
        if not isinstance(node_id, str) or not node_id:
            raise SemanticMaterializationError("accepted node lacks nodeID")
        evidence = node.get("evidenceOccurrences")
        if not isinstance(evidence, list):
            raise SemanticMaterializationError(f"accepted node {node_id} lacks evidenceOccurrences")
        result.append(deepcopy(dict(node)))
    ids = [str(row["nodeID"]) for row in result]
    if len(ids) != len(set(ids)):
        raise SemanticMaterializationError("accepted node IDs are not unique")
    return sorted(result, key=lambda row: str(row["nodeID"]))


def _valid_evidence(node: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Return valid evidence occurrences in canonical order."""

    return sorted(
        [deepcopy(dict(row)) for row in node["evidenceOccurrences"] if isinstance(row, Mapping) and row.get("valid") is True],
        key=lambda row: (
            str(row.get("canonicalPaperID", "")),
            str(row.get("sourceUnitID", "")),
            int(row.get("startOffsetInDocument", -1)),
            int(row.get("endOffsetInDocument", -1)),
            str(row.get("evidenceSpanID", "")),
        ),
    )


def _one_paper(node: Mapping[str, Any]) -> tuple[str, list[dict[str, Any]]]:
    """Resolve valid node evidence to exactly one canonical Paper or fail closed."""

    evidence = _valid_evidence(node)
    papers = {str(row.get("canonicalPaperID")) for row in evidence if row.get("canonicalPaperID")}
    if len(papers) != 1:
        raise SemanticMaterializationError(
            f"node {node['nodeID']} evidence resolves to {len(papers)} canonical Papers"
        )
    return next(iter(papers)), evidence


def _suppression_index(
    projection: Mapping[str, Any], policy: Mapping[str, Any]
) -> dict[tuple[str, str], list[dict[str, str]]]:
    """Index accepted stronger or specialized edges by exact endpoint pair."""

    suppressing = set(policy["stronger_role_relations"]) | set(policy["specialized_subproperties"])
    index: dict[tuple[str, str], list[dict[str, str]]] = {}
    for edge in projection.get("acceptedEdges", []):
        if not isinstance(edge, Mapping) or edge.get("accepted") is not True:
            continue
        name = str(edge.get("relationName", ""))
        if name not in suppressing:
            continue
        key = (str(edge.get("sourceID", "")), str(edge.get("targetID", "")))
        index.setdefault(key, []).append(
            {"edgeID": str(edge.get("edgeID", "")), "relationName": name}
        )
    for rows in index.values():
        rows.sort(key=lambda row: (row["relationName"], row["edgeID"]))
    return index


def _edge_id(source_id: str, target_id: str, derivation_kind: str) -> str:
    """Return the deterministic identity for one explicit fallback edge."""

    identity = canonical_json(
        {
            "derivationKind": derivation_kind,
            "derivationMethod": MATERIALIZER_VERSION,
            "ontologyRelationID": "D-26",
            "relationName": "mentions",
            "sourceID": source_id,
            "targetID": target_id,
        }
    )
    return f"derived-mentions-{hashlib.sha256(identity).hexdigest()[:24]}"


def _base_edge(
    source_id: str,
    target_id: str,
    derivation_kind: str,
    paper_id: str,
    entity_evidence_ids: Sequence[str],
    policy: Mapping[str, Any],
) -> dict[str, Any]:
    """Build common canonical D-26 edge content."""

    return {
        "edgeID": _edge_id(source_id, target_id, derivation_kind),
        "sourceID": source_id,
        "targetID": target_id,
        "ontologyRelationID": "D-26",
        "relationName": "mentions",
        "derivationKind": derivation_kind,
        "derivationMethodVersion": MATERIALIZER_VERSION,
        "canonicalPaperID": paper_id,
        "entityEvidenceSpanIDs": sorted(set(entity_evidence_ids)),
        "policyAuthority": {
            "policyID": policy["policy_id"],
            "policyVersion": policy["policy_version"],
            "policySha256": sha256_bytes(POLICY_PATH.read_bytes()),
        },
        "ontologyAuthority": deepcopy(policy["ontology"]),
    }


def materialize_generic_mentions(projection: Mapping[str, Any]) -> dict[str, Any]:
    """Materialize deterministic fallback D-26 edges from accepted semantics."""

    if projection.get("projectionVersion") != "publication-accepted-semantic-projection/0.1.0":
        raise SemanticMaterializationError("unsupported accepted-semantic projection version")
    if not isinstance(projection.get("acceptanceBasis"), str):
        raise SemanticMaterializationError("accepted projection lacks acceptanceBasis")
    spec, policy, domain_roots, range_roots = _ontology_authority()
    domain = _class_closure(spec, domain_roots)
    mentionable = _class_closure(spec, range_roots)
    nodes = _accepted_nodes(projection)
    node_ids = {str(row["nodeID"]): row for row in nodes}
    papers = {
        str(row["canonicalPaperID"]): row
        for row in projection.get("paperEndpoints", [])
        if isinstance(row, Mapping)
        and isinstance(row.get("canonicalPaperID"), str)
        and isinstance(row.get("nodeID"), str)
    }
    suppression = _suppression_index(projection, policy)
    before: list[dict[str, Any]] = []
    emitted: list[dict[str, Any]] = []
    suppressed: list[dict[str, Any]] = []

    entities: list[tuple[dict[str, Any], str, list[dict[str, Any]]]] = []
    discourses: list[tuple[dict[str, Any], str, list[dict[str, Any]]]] = []
    for node in nodes:
        class_name = str(node.get("className", ""))
        if class_name in mentionable:
            paper_id, evidence = _one_paper(node)
            entities.append((node, paper_id, evidence))
        if class_name in domain and class_name != "Paper":
            paper_id, evidence = _one_paper(node)
            discourses.append((node, paper_id, evidence))

    for entity, paper_id, entity_evidence in entities:
        paper = papers.get(paper_id)
        if paper is None:
            raise SemanticMaterializationError(
                f"no trusted Paper endpoint for canonical Paper {paper_id}"
            )
        edge = _base_edge(
            str(paper["nodeID"]), str(entity["nodeID"]), "paper_entity",
            paper_id, [str(row["evidenceSpanID"]) for row in entity_evidence], policy,
        )
        edge["sourcePaperProvenance"] = deepcopy(dict(paper))
        before.append(edge)
        blockers = suppression.get((edge["sourceID"], edge["targetID"]), [])
        if blockers:
            suppressed.append({"candidateEdge": edge, "suppressedBy": blockers})
        else:
            emitted.append(edge)

    for discourse, discourse_paper, discourse_evidence in discourses:
        for entity, entity_paper, entity_evidence in entities:
            if discourse["nodeID"] == entity["nodeID"] or discourse_paper != entity_paper:
                continue
            bindings: list[dict[str, Any]] = []
            for d_span in discourse_evidence:
                for e_span in entity_evidence:
                    if exact_coordinate_containment(d_span, e_span):
                        bindings.append(
                            {
                                "containmentRule": CONTAINMENT_TERM,
                                "discourseEvidenceSpanID": d_span["evidenceSpanID"],
                                "entityEvidenceSpanID": e_span["evidenceSpanID"],
                                "sourceUnitID": d_span["sourceUnitID"],
                                "canonicalPaperID": discourse_paper,
                                "discourseCoordinates": {key: d_span[key] for key in EVIDENCE_COORDINATES},
                                "entityCoordinates": {key: e_span[key] for key in EVIDENCE_COORDINATES},
                            }
                        )
            if not bindings:
                continue
            bindings.sort(
                key=lambda row: (row["sourceUnitID"], row["discourseEvidenceSpanID"], row["entityEvidenceSpanID"])
            )
            edge = _base_edge(
                str(discourse["nodeID"]), str(entity["nodeID"]), "discourse_entity",
                discourse_paper, [str(row["evidenceSpanID"]) for row in entity_evidence], policy,
            )
            edge["sourcePaperProvenance"] = deepcopy(dict(papers[discourse_paper]))
            edge["exactCoordinateContainmentBindings"] = bindings
            before.append(edge)
            blockers = suppression.get((edge["sourceID"], edge["targetID"]), [])
            if blockers:
                suppressed.append({"candidateEdge": edge, "suppressedBy": blockers})
            else:
                emitted.append(edge)

    before.sort(key=lambda row: row["edgeID"])
    emitted.sort(key=lambda row: row["edgeID"])
    suppressed.sort(key=lambda row: row["candidateEdge"]["edgeID"])
    result: dict[str, Any] = {
        "outputVersion": OUTPUT_VERSION,
        "outputStage": "post_acceptance_semantic_materialization",
        "acceptanceBasis": projection["acceptanceBasis"],
        "notModelAuthored": True,
        "derivedRelation": {"ontologyRelationID": "D-26", "relationName": "mentions"},
        "derivationCandidateCountBeforeSuppression": len(before),
        "derivationCounts": {
            "paperBeforeSuppression": sum(row["derivationKind"] == "paper_entity" for row in before),
            "paperAfterSuppression": sum(row["derivationKind"] == "paper_entity" for row in emitted),
            "discourseBeforeSuppression": sum(row["derivationKind"] == "discourse_entity" for row in before),
            "discourseAfterSuppression": sum(row["derivationKind"] == "discourse_entity" for row in emitted),
            "exactCoordinateContainmentBindingCount": sum(
                len(row.get("exactCoordinateContainmentBindings", [])) for row in before
            ),
        },
        "derivedEdges": emitted,
        "suppressedDerivations": suppressed,
    }
    result["canonicalOutputSha256"] = sha256_bytes(canonical_json(result))
    return result
