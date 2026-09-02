"""Bind trusted edge endpoint artifact metadata before canonical validation."""

from __future__ import annotations

from collections import Counter
from copy import deepcopy
import re
from typing import Any, Mapping


ENDPOINT_BINDING_VERSION = "publication-deterministic-endpoint-binding-0.1.0"
_CANDIDATE_NODE_ID = re.compile(r"^node-[0-9]{4}$")
_REFERENCE_TYPES = frozenset({
    "candidate_node", "deterministic_node", "accepted_local_candidate",
})


def _authorized_artifact_index(
    rows: object, id_key: str, pointer: str
) -> tuple[dict[str, str], list[dict[str, str]]]:
    """Index one trusted endpoint collection without silently resolving duplicates."""

    findings: list[dict[str, str]] = []
    if not isinstance(rows, list):
        return {}, [{"code": "ENDPOINT_BINDING_AUTHORITY_NOT_ARRAY", "pointer": pointer}]
    identifiers = [str(row.get(id_key)) for row in rows if isinstance(row, Mapping)]
    counts = Counter(identifiers)
    indexed: dict[str, str] = {}
    for index, row in enumerate(rows):
        row_pointer = f"{pointer}/{index}"
        if not isinstance(row, Mapping):
            findings.append({"code": "ENDPOINT_BINDING_AUTHORITY_NOT_OBJECT", "pointer": row_pointer})
            continue
        reference_id = row.get(id_key)
        artifact_id = row.get("artifactID")
        if not isinstance(reference_id, str) or not reference_id:
            findings.append({"code": "ENDPOINT_BINDING_AUTHORITY_REFERENCE_INVALID", "pointer": row_pointer + f"/{id_key}"})
            continue
        if counts[reference_id] != 1:
            findings.append({"code": "ENDPOINT_BINDING_AUTHORITY_REFERENCE_AMBIGUOUS", "pointer": row_pointer + f"/{id_key}"})
            continue
        if not isinstance(artifact_id, str) or not artifact_id:
            findings.append({"code": "ENDPOINT_BINDING_AUTHORITY_ARTIFACT_INVALID", "pointer": row_pointer + "/artifactID"})
            continue
        indexed[reference_id] = artifact_id
    return indexed, findings


def bind_edge_endpoint_artifact_ids(
    payload: Mapping[str, Any], request: Mapping[str, Any]
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Inject canonical endpoint artifact IDs using only exact trusted references.

    The model remains responsible solely for ``referenceType`` and ``referenceID``.
    Any malformed, unknown, ambiguous, or model-authored artifact field fails closed;
    this function never uses labels, sourceArtifactID, similarity, or a fallback ID.
    """

    bound = deepcopy(dict(payload))
    findings: list[dict[str, str]] = []
    nodes = bound.get("candidateNodes", [])
    edges = bound.get("candidateEdges", [])
    if not isinstance(nodes, list):
        findings.append({"code": "ENDPOINT_BINDING_CANDIDATE_NODES_NOT_ARRAY", "pointer": "/candidateNodes"})
        nodes = []
    if not isinstance(edges, list):
        findings.append({"code": "ENDPOINT_BINDING_CANDIDATE_EDGES_NOT_ARRAY", "pointer": "/candidateEdges"})
        edges = []
    node_ids = [row.get("candidateID") for row in nodes if isinstance(row, Mapping)]
    node_counts = Counter(node_ids)
    deterministic, deterministic_findings = _authorized_artifact_index(
        request.get("deterministicEndpoints", []), "nodeID", "/request/deterministicEndpoints"
    )
    accepted, accepted_findings = _authorized_artifact_index(
        request.get("acceptedLocalCandidateEndpoints", []), "candidateID", "/request/acceptedLocalCandidateEndpoints"
    )
    findings.extend(deterministic_findings)
    findings.extend(accepted_findings)

    for edge_index, edge in enumerate(edges):
        edge_pointer = f"/candidateEdges/{edge_index}"
        if not isinstance(edge, dict):
            findings.append({"code": "ENDPOINT_BINDING_EDGE_NOT_OBJECT", "pointer": edge_pointer})
            continue
        for side in ("source", "target"):
            pointer = edge_pointer + f"/{side}"
            endpoint = edge.get(side)
            if not isinstance(endpoint, dict):
                findings.append({"code": "ENDPOINT_BINDING_ENDPOINT_NOT_OBJECT", "pointer": pointer})
                continue
            if "artifactID" in endpoint:
                findings.append({"code": "ENDPOINT_BINDING_MODEL_AUTHORED_ARTIFACT_ID", "pointer": pointer + "/artifactID"})
                continue
            reference_type = endpoint.get("referenceType")
            reference_id = endpoint.get("referenceID")
            if reference_type not in _REFERENCE_TYPES:
                findings.append({"code": "ENDPOINT_BINDING_REFERENCE_TYPE_INVALID", "pointer": pointer + "/referenceType"})
                continue
            if not isinstance(reference_id, str) or not reference_id:
                findings.append({"code": "ENDPOINT_BINDING_REFERENCE_ID_INVALID", "pointer": pointer + "/referenceID"})
                continue
            if reference_type == "candidate_node":
                if not _CANDIDATE_NODE_ID.fullmatch(reference_id):
                    findings.append({"code": "ENDPOINT_BINDING_CANDIDATE_REFERENCE_MALFORMED", "pointer": pointer + "/referenceID"})
                elif node_counts[reference_id] != 1:
                    findings.append({"code": "ENDPOINT_BINDING_CANDIDATE_REFERENCE_UNRESOLVED", "pointer": pointer + "/referenceID"})
                else:
                    endpoint["artifactID"] = None
            elif reference_type == "deterministic_node":
                artifact_id = deterministic.get(reference_id)
                if artifact_id is None:
                    findings.append({"code": "ENDPOINT_BINDING_DETERMINISTIC_REFERENCE_UNRESOLVED", "pointer": pointer + "/referenceID"})
                else:
                    endpoint["artifactID"] = artifact_id
            else:
                artifact_id = accepted.get(reference_id)
                if artifact_id is None:
                    findings.append({"code": "ENDPOINT_BINDING_ACCEPTED_LOCAL_REFERENCE_UNRESOLVED", "pointer": pointer + "/referenceID"})
                else:
                    endpoint["artifactID"] = artifact_id
    return bound, {
        "bindingVersion": ENDPOINT_BINDING_VERSION,
        "bindingStatus": "bound" if not findings else "failed",
        "findings": findings,
    }
