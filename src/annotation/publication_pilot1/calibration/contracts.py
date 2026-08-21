"""Load frozen contracts for Publication Pilot 1 Annotation / Calibration Mode.

Production source text is reconstructed mechanically from the canonical source and frozen
inventory. Default synthetic mode uses discarded in-memory fixtures and never reads the
text of any real calibration unit.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

import yaml

from ..contracts import _canonical_text, sha256_file
from . import (
    ANNOTATION_OUTPUT_SCHEMA_VERSION,
    CONTEXT_POLICY_NAME,
    CONTEXT_POLICY_VERSION,
    GUIDELINE_VERSION,
    HANDBOOK_VERSION,
    INTERFACE_VERSION,
    ROUTING_VERSION,
)


CALIBRATION_ID_ORDER_HASH = "182710041594edb979dcfd8e39041cf98523e383c9f3498ac1d74293d0378b98"
CANDIDATE_ID_ORDER_HASH = "e95429c597fc6de4256c9a69343e1cda52d8b9414571264d90fc3087a1c4a40b"
ACTIVATION_PHRASE = "ACTIVATE_PUBLICATION_PILOT1_CALIBRATION_V1"
REGRESSION_SOURCE_UNIT_ID = "pub:34:sec:0028:unit:0001"
ANNOTATION_MVP_BASE_CHECKPOINT = "a67c5f3d70a3f4a71f79561646572781eeae89b4"
ACTIVATION_SCHEMA_VERSION = "0.1.0"

PROTECTED_HASHES = {
    "data/curation/papers/pilot1/publication_pilot1_source_unit_inventory.jsonl": "7a3a4941e6c07deee96b19c7619e0b9c5000ad6fadf5bf17379e37229562b07e",
    "data/curation/papers/pilot1/publication_pilot1_source_unit_manifest.json": "42684d340af99440d5f72129a5c5299edcb237d77ce2b3d36456b049bee83823",
    "src/extraction/llm/publications/publication_target_inventory.yaml": "3d8a80c4ff8794588e2551e63a61e72c60a9afcb89d8b7a7058ff23e25ee4760",
    "data/curation/papers/pilot1/publication_pilot1_selection_policy.yaml": "e977a77da4dc49e6f1ad3a283c60ccb2f2dbf391ac9d2541f60c8dc7d80526c3",
    "data/curation/papers/pilot1/publication_pilot1_target_coverage_matrix.csv": "b67fabb4c7b03b2e4b578c29e932f0122372a2d62f93cb5b172d90d798c9d109",
    "data/curation/papers/pilot1/publication_pilot1_pre_gate0_candidate_order.json": "186abc60950fca5596b6db5d73e9c56d555958f52d2305f34ac57c537649dfac",
    "data/curation/papers/pilot1/publication_pilot1_screening.jsonl": "a34e2ca153a066cf58188f1d332e62b4077622bd5b3a2c1a68939a24c0a0db90",
    "data/curation/papers/pilot1/publication_pilot1_unit_routing.jsonl": "66725306608139ccf3647ac7fd4a9fc150df67426498b6e3e7408320cb8c4a1f",
    "schemas/publication_pilot1_unit_routing.schema.json": "49af68b0ab47a5bbd29b6d10c382aee6252a1d5a3c1d0510c13e4673775c329f",
    "data/curation/papers/pilot1/publication_pilot1_calibration_manifest.json": "e9d761224b1c3c76c89bc6d7d63ca1f3b309e3155c4a191bbdfd66f380355d76",
    "data/curation/papers/pilot1/publication_pilot1_gate0_policy.yaml": "f9285a4912e55a154d9037e7fa97a6176f1e37194272ec6907ce8af4f10888ae",
    "data/curation/papers/pilot1/publication_pilot1_target_display_catalog.yaml": "06ce672fd0ab66a8faa46bb4a870778c99acebf9cdd242be8b8a0dba493cae96",
    "data/curation/papers/pilot1/publication_pilot1_target_family_mapping.yaml": "fbf1da8f43174791a160106014975fd7084c18de5df2f14a5203368418f081fe",
    "schemas/publication_candidate_output.schema.json": "affd13215dc8023723e7e497f6fce9696cbf8af9bb7c01a85e8aa560033a776d",
    "docs/publication_evidence_validation_contract.md": "3529484f74f9c482bd38c68c9bafbc08723e6dfd960e3c8d5faa70e1b6d28ce2",
    "docs/publication_annotation_adjudication_guidelines.md": "67d693edf8e42318a763aac58190675c90b944440dc12fce164212cf9552bd60",
    "docs/publication_evaluation_matching_contract.md": "10f8dca24bf41acfb21f8d20c5cda7b022392040446a2e2e4bac137365c076d0",
    "data/interim/papers/publication_nodes_edges.json": "675049dae5c3dfed6f492ad0aa79e27fc1a9b37d0ecbc13ab3cf1a69cdb8efaf",
}
PRIVATE_SCREENING_RELATIVE = "var/publication_pilot1_screening/exports/publication_pilot1_screening_worklist_reviewed.csv"
PRIVATE_SCREENING_HASH = "2cba7bdb025f063b0cfbc0b05c375feee341231b34926abe43e7cd9790ce2c01"


class AnnotationContractError(ValueError):
    """Report a stable annotation-interface contract failure."""


def canonical_json_hash(value: object) -> str:
    """Hash deterministic compact JSON using UTF-8."""

    data = json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(data).hexdigest()


def verify_protected_hashes(root: Path) -> dict[str, str]:
    """Fail closed when an accepted public or private authority drifts."""

    observed: dict[str, str] = {}
    for relative, expected in PROTECTED_HASHES.items():
        path = root / relative
        if not path.is_file():
            raise AnnotationContractError(f"ANNOTATION_UPSTREAM_FILE_MISSING:{relative}")
        observed[relative] = sha256_file(path)
        if observed[relative] != expected:
            raise AnnotationContractError(f"ANNOTATION_UPSTREAM_HASH_MISMATCH:{relative}")
    private = root / PRIVATE_SCREENING_RELATIVE
    if not private.is_file() or sha256_file(private) != PRIVATE_SCREENING_HASH:
        raise AnnotationContractError("ANNOTATION_PRIVATE_SCREENING_HASH_MISMATCH")
    observed[PRIVATE_SCREENING_RELATIVE] = PRIVATE_SCREENING_HASH
    return observed


def _jsonl_index(path: Path, *, omit_source_text: bool = False) -> dict[str, dict[str, Any]]:
    """Load a sourceUnitID-keyed JSONL artifact."""

    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]
    if omit_source_text:
        for row in rows:
            row.pop("text", None)
    return {str(row["sourceUnitID"]): row for row in rows}


def _frozen_inventory_text(root: Path, source_unit_id: str) -> str:
    """Read one accepted inventory text field only at deliberate production unit open."""

    path = root / "data/curation/papers/pilot1/publication_pilot1_source_unit_inventory.jsonl"
    for line in path.read_text(encoding="utf-8").splitlines():
        if line:
            row = json.loads(line)
            if row.get("sourceUnitID") == source_unit_id:
                return str(row["text"])
    raise AnnotationContractError(f"ANNOTATION_SOURCE_UNIT_UNKNOWN:{source_unit_id}")


def _phase_b_nodes(root: Path, expected_hash: str) -> dict[str, dict[str, Any]]:
    """Index exact frozen Phase-B nodes after verifying the manifest-bound artifact hash."""

    path = root / "data/interim/papers/publication_nodes_edges.json"
    if sha256_file(path) != expected_hash:
        raise AnnotationContractError("ANNOTATION_PHASE_B_ARTIFACT_HASH_MISMATCH")
    payload = json.loads(path.read_text(encoding="utf-8"))
    rows = payload.get("nodes", [])
    if not isinstance(rows, list):
        raise AnnotationContractError("ANNOTATION_PHASE_B_NODES_INVALID")
    result: dict[str, dict[str, Any]] = {}
    for row in rows:
        node_id = row.get("id") if isinstance(row, Mapping) else None
        if not isinstance(node_id, str) or not node_id or node_id in result:
            raise AnnotationContractError("ANNOTATION_PHASE_B_NODE_ID_INVALID")
        result[node_id] = dict(row)
    return result


def _deterministic_label(node: Mapping[str, Any]) -> str:
    """Derive a concise display label without using it for endpoint resolution."""

    attributes = node.get("attributes", {})
    if not isinstance(attributes, Mapping):
        attributes = {}
    for key in ("title", "name", "identifierValue", "htmlUrl", "doi", "canonicalArtifactId"):
        value = attributes.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    canonical_key = node.get("canonicalKey")
    return str(canonical_key or node["id"])


def resolve_deterministic_endpoints(
    units: Mapping[str, Mapping[str, Any]],
    source_unit_ids: Sequence[str],
    phase_b_nodes: Mapping[str, Mapping[str, Any]],
) -> dict[str, dict[str, str]]:
    """Resolve only exact source-unit Phase-B node references to frozen identities."""

    result: dict[str, dict[str, str]] = {}
    for source_unit_id in source_unit_ids:
        unit = units[source_unit_id]
        for reference in unit.get("deterministicNodeRefs", []):
            if not isinstance(reference, str) or reference not in phase_b_nodes:
                raise AnnotationContractError(f"ANNOTATION_DETERMINISTIC_NODE_REF_UNRESOLVED:{reference}")
            node = phase_b_nodes[reference]
            class_name = node.get("class")
            if not isinstance(class_name, str) or not class_name:
                raise AnnotationContractError(f"ANNOTATION_DETERMINISTIC_NODE_CLASS_INVALID:{reference}")
            attributes = node.get("attributes", {}) if isinstance(node.get("attributes"), Mapping) else {}
            represented_artifact = (
                attributes.get("canonicalArtifactId") or attributes.get("htmlUrl")
                or attributes.get("identifierUri") or node.get("canonicalKey") or reference
            )
            result[reference] = {
                "className": class_name,
                "artifactID": str(represented_artifact),
                "displayLabel": _deterministic_label(node),
            }
    return result


def _profile(root: Path) -> Mapping[str, Any]:
    """Load the accepted target profile."""

    return yaml.safe_load(
        (root / "src/extraction/llm/publications/publication_target_inventory.yaml").read_text(encoding="utf-8")
    )


def _target_indexes(root: Path) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]], Mapping[str, Sequence[str]]]:
    """Index every concrete operational annotation target and class expansion."""

    profile = _profile(root)
    treatments = {"extract_and_evaluate", "extract_and_monitor", "deferred_resolution"}
    nodes = {
        row["operational_id"]: row for row in profile["node_targets"]
        if row.get("direct_instantiation") and row.get("pilot_treatment") in treatments
    }
    relations = {
        row["operational_id"]: row for row in profile["relation_targets"]
        if row.get("pilot_treatment") in treatments and row.get("allowed_actions")
    }
    return nodes, relations, profile["class_expansions"]


def _display_index(root: Path) -> dict[str, dict[str, Any]]:
    """Index the accepted human-readable display catalog."""

    catalog = yaml.safe_load(
        (root / "data/curation/papers/pilot1/publication_pilot1_target_display_catalog.yaml").read_text(encoding="utf-8")
    )
    return {row["operationalTargetID"]: row for row in catalog["targets"]}


def validate_effective_route(
    route: Mapping[str, Any], unit: Mapping[str, Any], deferred_target_ids: set[str]
) -> None:
    """Validate routing 0.1.2 availability without recreating Block A decisions."""

    if route.get("routingVersion") != ROUTING_VERSION:
        raise AnnotationContractError(f"ANNOTATION_ROUTING_VERSION_MISMATCH:{route.get('sourceUnitID')}")
    effective_nodes = set(route.get("eligibleNodeOperationalTargetIDs", []))
    effective_relations = set(route.get("eligibleRelationOperationalTargetIDs", []))
    screened_nodes = set(route.get("humanScreenedNodeOperationalTargetIDs", []))
    screened_relations = set(route.get("humanScreenedRelationOperationalTargetIDs", []))
    unavailable = route.get("structurallyUnavailableOperationalTargets", [])
    unavailable_ids = {row["operationalTargetID"] for row in unavailable}
    if not effective_nodes <= screened_nodes or not effective_relations <= screened_relations:
        raise AnnotationContractError("ANNOTATION_EFFECTIVE_ROUTE_NOT_SCREENED_SUBSET")
    if (effective_nodes | effective_relations) & unavailable_ids:
        raise AnnotationContractError("ANNOTATION_STRUCTURALLY_UNAVAILABLE_TARGET_EFFECTIVE")
    for row in unavailable:
        if row.get("pilotTreatment") != "deferred_resolution" or row.get("reason") != "deferred_record_binding_absent":
            raise AnnotationContractError("ANNOTATION_STRUCTURAL_UNAVAILABILITY_RECORD_INVALID")
    deferred_refs = list(unit.get("deferredRecordRefs", []))
    effective_ids = effective_nodes | effective_relations
    if effective_ids & deferred_target_ids and not deferred_refs:
        raise AnnotationContractError("ANNOTATION_DEFERRED_TARGET_WITHOUT_EXACT_BINDING")


@dataclass(frozen=True)
class AnnotationContracts:
    """Validated units, effective routes, targets, and immutable bindings."""

    root: Path
    mode: str
    units_by_id: Mapping[str, Mapping[str, Any]]
    routes_by_id: Mapping[str, Mapping[str, Any]]
    unit_order: tuple[str, ...]
    node_targets: Mapping[str, Mapping[str, Any]]
    relation_targets: Mapping[str, Mapping[str, Any]]
    displays: Mapping[str, Mapping[str, Any]]
    class_expansions: Mapping[str, Sequence[str]]
    hashes: Mapping[str, str]
    canonical_document_hashes: Mapping[str, str]
    phase_b_nodes: Mapping[str, Mapping[str, Any]]

    def canonical_document_hash(self, source_unit_id: str) -> str:
        """Return and cross-check the accepted artifact-level canonical-text hash."""

        unit = self.units_by_id.get(source_unit_id)
        if unit is None:
            raise AnnotationContractError(f"ANNOTATION_SOURCE_UNIT_UNKNOWN:{source_unit_id}")
        expected = self.canonical_document_hashes.get(str(unit["paperID"]))
        if not expected or unit.get("canonicalTextSha256") != expected:
            raise AnnotationContractError(f"ANNOTATION_CANONICAL_DOCUMENT_HASH_DRIFT:{source_unit_id}")
        return expected

    def canonical_document_text(self, source_unit_id: str) -> str:
        """Load the canonical document for document-offset evidence validation."""

        unit = self.units_by_id[source_unit_id]
        if self.mode == "synthetic":
            document = str(unit["syntheticDocumentText"])
        else:
            path = self.root / str(unit["sourceFile"])
            if not path.is_file():
                raise AnnotationContractError(f"ANNOTATION_SOURCE_FILE_MISSING:{unit['sourceFile']}")
            document = _canonical_text(path)
        if hashlib.sha256(document.encode("utf-8")).hexdigest() != self.canonical_document_hash(source_unit_id):
            raise AnnotationContractError(f"ANNOTATION_CANONICAL_DOCUMENT_TEXT_HASH_MISMATCH:{source_unit_id}")
        return document

    def context_candidate_ids(self, primary_source_unit_id: str, *, same_section: bool | None = None) -> tuple[str, ...]:
        """Return bounded human-context candidates without loading their source text."""

        primary = self.units_by_id[primary_source_unit_id]
        rows = []
        for unit_id, unit in self.units_by_id.items():
            if unit_id == primary_source_unit_id or unit.get("paperID") != primary.get("paperID"):
                continue
            if unit.get("eligibility") not in {"eligible", "context_only"}:
                continue
            is_same_section = unit.get("sectionID") == primary.get("sectionID")
            if same_section is not None and is_same_section != same_section:
                continue
            rows.append(unit_id)
        return tuple(sorted(rows, key=lambda unit_id: (
            int(self.units_by_id[unit_id]["startOffsetInDocument"]), unit_id,
        )))

    def authorized_context_ids(
        self, primary_source_unit_id: str, exposed_context_ids: Sequence[str] = (),
    ) -> tuple[str, ...]:
        """Validate and return the primary plus explicitly exposed bounded context."""

        candidates = set(self.context_candidate_ids(primary_source_unit_id))
        exposed = tuple(dict.fromkeys(str(value) for value in exposed_context_ids))
        if not set(exposed) <= candidates:
            raise AnnotationContractError("ANNOTATION_CONTEXT_UNIT_NOT_AUTHORIZED")
        return (primary_source_unit_id, *exposed)

    def discovery_scope(
        self, primary_source_unit_id: str, evidence_unit_ids: Sequence[str],
        exposed_context_ids: Sequence[str] = (),
    ) -> str:
        """Derive the narrowest frozen discovery scope from cited canonical units."""

        if not evidence_unit_ids:
            raise AnnotationContractError("ANNOTATION_DISCOVERY_SCOPE_EVIDENCE_REQUIRED")
        authorized = set(self.authorized_context_ids(primary_source_unit_id, exposed_context_ids))
        if not set(evidence_unit_ids) <= authorized:
            raise AnnotationContractError("ANNOTATION_CONTEXT_UNIT_NOT_AUTHORIZED")
        if set(evidence_unit_ids) == {primary_source_unit_id}:
            return "local_unit"
        primary_section = self.units_by_id[primary_source_unit_id]["sectionID"]
        if all(self.units_by_id[unit_id]["sectionID"] == primary_section for unit_id in evidence_unit_ids):
            return "section_context"
        return "document_reconciliation"

    def deterministic_endpoints(
        self, primary_source_unit_id: str, exposed_context_ids: Sequence[str] = (),
    ) -> dict[str, dict[str, str]]:
        """Return exact endpoints supplied by the authorized source-unit context."""

        return resolve_deterministic_endpoints(
            self.units_by_id,
            self.authorized_context_ids(primary_source_unit_id, exposed_context_ids),
            self.phase_b_nodes,
        )

    def source_text(self, source_unit_id: str) -> str:
        """Reconstruct exact text and validate code-point length and UTF-8 hash."""

        unit = self.units_by_id.get(source_unit_id)
        if unit is None:
            raise AnnotationContractError(f"ANNOTATION_SOURCE_UNIT_UNKNOWN:{source_unit_id}")
        if self.mode == "synthetic":
            text = str(unit["text"])
        else:
            source_path = self.root / str(unit["sourceFile"])
            if not source_path.is_file():
                raise AnnotationContractError(f"ANNOTATION_SOURCE_FILE_MISSING:{unit['sourceFile']}")
            document = _canonical_text(source_path)
            start, end = int(unit["startOffsetInDocument"]), int(unit["endOffsetInDocument"])
            text = document[start:end]
            if text != _frozen_inventory_text(self.root, source_unit_id):
                raise AnnotationContractError(f"ANNOTATION_SOURCE_RECONSTRUCTION_MISMATCH:{source_unit_id}")
        if hashlib.sha256(text.encode("utf-8")).hexdigest() != unit["textHash"]:
            raise AnnotationContractError(f"ANNOTATION_SOURCE_TEXT_HASH_MISMATCH:{source_unit_id}")
        if len(text) != int(unit["characterCount"]):
            raise AnnotationContractError(f"ANNOTATION_SOURCE_CODEPOINT_LENGTH_MISMATCH:{source_unit_id}")
        return text


def _synthetic_contracts(root: Path, hashes: Mapping[str, str]) -> AnnotationContracts:
    """Create discarded fixtures that exercise Unicode and effective routing."""

    nodes, relations, expansions = _target_indexes(root)
    deferred_ids = {
        target_id for target_id, target in {**nodes, **relations}.items()
        if target["pilot_treatment"] == "deferred_resolution"
    }
    primary_text = (
        "Café flow 😀 was evaluated with RMSE. The method produced a clear finding. "
        "Repository fork commit abc123; we used the R package hydroGOF."
    )
    section_text = "The reported value was 0.82 and the parameter range was 2–5."
    context_only_text = "A section heading supplies context but is not an open annotation unit."
    document_text = "Calibration used the default parameter in a separate results section."
    later_document_text = "A later discussion remains unexposed until separately requested."
    second_text = "The naïve model uses rainfall data and applies to Río Álamo."
    first_document = "\n".join((primary_text, section_text, context_only_text, document_text, later_document_text))
    documents = {"synthetic": first_document, "synthetic-2": second_text}
    unit_specs = (
        ("synthetic:publication:unit:0001", "synthetic", "synthetic:section:0001", primary_text, 0),
        ("synthetic:publication:context:0001", "synthetic", "synthetic:section:0001", section_text, len(primary_text) + 1),
        ("synthetic:publication:context-only:0001", "synthetic", "synthetic:section:0001", context_only_text, len(primary_text) + len(section_text) + 2),
        ("synthetic:publication:context:0002", "synthetic", "synthetic:section:0002", document_text, len(primary_text) + len(section_text) + len(context_only_text) + 3),
        ("synthetic:publication:context:0003", "synthetic", "synthetic:section:0003", later_document_text, len(primary_text) + len(section_text) + len(context_only_text) + len(document_text) + 4),
        ("synthetic:publication:unit:0002", "synthetic-2", "synthetic:section:0003", second_text, 0),
    )
    ids = ("synthetic:publication:unit:0001", "synthetic:publication:unit:0002")
    node_routes = (
        ["PUB-N-A-P13-METHOD", "PUB-N-A-P16-FINDING", "PUB-N-A-DOM02-TOOL-NEW-FROM-PUBLICATION-PROSE", "PUB-N-A-DOM11-EVALUATIONMETRIC", "PUB-N-A-DOM12-PARAMETER", "PUB-N-A-C01-REPOSITORY-NAMED-WITHOUT-EXACT-IDENTITY", "PUB-N-A-P05-BACKGROUND"],
        ["PUB-N-A-DOM03C-STATISTICALMODEL", "PUB-N-A-P25-DATASETMENTION-NEW-FROM-PROSE", "PUB-N-A-DOM08-NAMEDPLACE"],
    )
    relation_routes = (
        ["PUB-R-C-P07-PRODUCES", "PUB-R-C-P25-REPORTSMETRIC", "PUB-R-C-P32-REFERENCESREPOSITORY"],
        ["PUB-R-C-P20-USESDATASET-NEW-PROSE-EVIDENCE", "PUB-R-C-P14-APPLIESTO"],
    )
    deferred_node = "PUB-N-A-D01-DATASETRESOURCE-EXACT-IDENTIFIER-OMITTED-BY-PHASE-B"
    deferred_relation = "PUB-R-C-P29-REFERENCESDATASET-EXACT-OMITTED-IDENTIFIER"
    exact_repository = "publication:repository:0603320a21f133eb4ad8"
    exact_context_tool = "publication:tool:07b292b28372c3181bec"
    phase_b_manifest = json.loads(
        (root / "data/curation/papers/pilot1/publication_pilot1_source_unit_manifest.json").read_text(encoding="utf-8")
    )
    phase_nodes = _phase_b_nodes(root, str(phase_b_manifest["phaseBArtifactHash"]))
    units: dict[str, dict[str, Any]] = {}
    routes: dict[str, dict[str, Any]] = {}
    for index, (unit_id, paper_id, section_id, text, start_offset) in enumerate(unit_specs, start=1):
        text_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()
        units[unit_id] = {
            "sourceUnitID": unit_id, "canonicalArtifactID": f"synthetic:discarded:publication:{paper_id}",
            "paperID": paper_id, "sectionID": section_id,
            "sectionTitleRaw": f"Discarded synthetic section {index}", "sectionRole": "synthetic",
            "startOffsetInDocument": start_offset, "endOffsetInDocument": start_offset + len(text),
            "characterCount": len(text), "canonicalTextSha256": hashlib.sha256(documents[paper_id].encode("utf-8")).hexdigest(),
            "syntheticDocumentText": documents[paper_id],
            "text": text, "textHash": text_hash,
            "eligibility": "context_only" if "context-only" in unit_id else "eligible",
            "requestEligible": "context-only" not in unit_id,
            "deferredRecordRefs": [],
            "deterministicNodeRefs": (
                [exact_repository] if unit_id == ids[0]
                else [exact_context_tool] if unit_id == "synthetic:publication:context:0002" else []
            ),
            "deterministicEdgeRefs": [],
        }
    for index, unit_id in enumerate(ids):
        unit = units[unit_id]
        text_hash = unit["textHash"]
        historical_nodes = list(node_routes[index])
        historical_relations = list(relation_routes[index])
        unavailable = []
        if index == 0:
            historical_nodes.append(deferred_node)
            historical_relations.append(deferred_relation)
            unavailable = [
                {"operationalTargetID": deferred_node, "targetKind": "node", "pilotTreatment": "deferred_resolution", "reason": "deferred_record_binding_absent"},
                {"operationalTargetID": deferred_relation, "targetKind": "relation", "pilotTreatment": "deferred_resolution", "reason": "deferred_record_binding_absent"},
            ]
        routes[unit_id] = {
            "sourceUnitID": unit_id, "sourceUnitTextHash": text_hash,
            "sourceArtifactID": unit["canonicalArtifactID"], "paperID": unit["paperID"],
            "sectionID": unit["sectionID"], "sectionRole": "synthetic",
            "routingStatus": "routed", "routingVersion": ROUTING_VERSION, "routingDoesNotAssertPresence": True,
            "humanScreenedNodeOperationalTargetIDs": historical_nodes,
            "humanScreenedRelationOperationalTargetIDs": historical_relations,
            "eligibleNodeOperationalTargetIDs": list(node_routes[index]),
            "eligibleRelationOperationalTargetIDs": list(relation_routes[index]),
            "structurallyUnavailableOperationalTargets": unavailable, "deterministicEndpointRefs": [],
        }
        validate_effective_route(routes[unit_id], units[unit_id], deferred_ids)
    canonical_hashes = {paper_id: hashlib.sha256(text.encode("utf-8")).hexdigest() for paper_id, text in documents.items()}
    return AnnotationContracts(
        root, "synthetic", units, routes, ids, nodes, relations, _display_index(root), expansions,
        hashes, canonical_hashes, phase_nodes,
    )


def production_activation_payload(
    root: Path, annotator_id: str, annotation_session_id: str, *, package_build_checkpoint: str,
) -> dict[str, Any]:
    """Build the exact deterministic researcher-issued production activation payload."""

    annotator = annotator_id.strip(); session = annotation_session_id.strip()
    if not annotator or not session:
        raise AnnotationContractError("CALIBRATION_ACTIVATION_IDENTITY_REQUIRED")
    if len(package_build_checkpoint) != 40 or any(character not in "0123456789abcdef" for character in package_build_checkpoint):
        raise AnnotationContractError("CALIBRATION_PACKAGE_BUILD_CHECKPOINT_INVALID")
    hashes = verify_protected_hashes(root)
    calibration_manifest = json.loads(
        (root / "data/curation/papers/pilot1/publication_pilot1_calibration_manifest.json").read_text(encoding="utf-8")
    )
    return {
        "activationSchemaVersion": ACTIVATION_SCHEMA_VERSION,
        "activation": ACTIVATION_PHRASE,
        "mode": "calibration",
        "annotationMVPBaseCheckpoint": ANNOTATION_MVP_BASE_CHECKPOINT,
        "packageBuildCheckpoint": package_build_checkpoint,
        "annotatorID": annotator,
        "annotationSessionID": session,
        "interfaceVersion": INTERFACE_VERSION,
        "annotationSchemaVersion": ANNOTATION_OUTPUT_SCHEMA_VERSION,
        "guidelineVersion": GUIDELINE_VERSION,
        "guidelineHash": hashes["docs/publication_annotation_adjudication_guidelines.md"],
        "handbookVersion": HANDBOOK_VERSION,
        "routingVersion": ROUTING_VERSION,
        "contextPolicyName": CONTEXT_POLICY_NAME,
        "contextPolicyVersion": CONTEXT_POLICY_VERSION,
        "calibrationCount": 16,
        "calibrationManifestVersion": calibration_manifest["calibrationManifestVersion"],
        "calibrationIdentityOrderHash": CALIBRATION_ID_ORDER_HASH,
        "sourceUnitInventoryHash": hashes["data/curation/papers/pilot1/publication_pilot1_source_unit_inventory.jsonl"],
        "calibrationManifestHash": hashes["data/curation/papers/pilot1/publication_pilot1_calibration_manifest.json"],
        "routingHash": hashes["data/curation/papers/pilot1/publication_pilot1_unit_routing.jsonl"],
        "gate0PolicyHash": hashes["data/curation/papers/pilot1/publication_pilot1_gate0_policy.yaml"],
        "annotationSchemaHash": sha256_file(root / "schemas/publication_pilot1_annotation_record.schema.json"),
        "handbookHash": sha256_file(root / "docs/publication_pilot1_annotation_calibration_handbook.md"),
    }


def verify_production_activation(
    path: Path | None, root: Path, *, annotator_id: str | None = None,
    annotation_session_id: str | None = None, expected_package_build_checkpoint: str | None = None,
) -> dict[str, Any]:
    """Require exact checkpoint, identity, version, and input bindings before production state."""

    if path is None or not path.is_file():
        raise AnnotationContractError("CALIBRATION_PRODUCTION_ACTIVATION_REQUIRED")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        raise AnnotationContractError("CALIBRATION_PRODUCTION_ACTIVATION_INVALID") from exc
    payload_annotator = payload.get("annotatorID") if annotator_id is None else annotator_id
    payload_session = payload.get("annotationSessionID") if annotation_session_id is None else annotation_session_id
    package_checkpoint = (
        payload.get("packageBuildCheckpoint")
        if expected_package_build_checkpoint is None else expected_package_build_checkpoint
    )
    expected = production_activation_payload(
        root, str(payload_annotator or ""), str(payload_session or ""),
        package_build_checkpoint=str(package_checkpoint or ""),
    )
    if payload != expected:
        raise AnnotationContractError("CALIBRATION_PRODUCTION_ACTIVATION_BINDING_MISMATCH")
    return payload


def load_annotation_contracts(root: Path, *, mode: str = "synthetic", activation_path: Path | None = None) -> AnnotationContracts:
    """Load synthetic defaults or guarded production-calibration metadata."""

    root = root.resolve()
    hashes = verify_protected_hashes(root)
    if mode == "synthetic":
        return _synthetic_contracts(root, hashes)
    if mode != "calibration":
        raise AnnotationContractError(f"ANNOTATION_MODE_UNKNOWN:{mode}")
    verify_production_activation(activation_path, root)
    manifest = json.loads((root / "data/curation/papers/pilot1/publication_pilot1_calibration_manifest.json").read_text(encoding="utf-8"))
    order_ids = tuple(manifest["calibrationSourceUnitIDs"])
    if len(order_ids) != 16 or len(set(order_ids)) != 16:
        raise AnnotationContractError("CALIBRATION_MANIFEST_CARDINALITY_MISMATCH")
    if canonical_json_hash(list(order_ids)) != CALIBRATION_ID_ORDER_HASH:
        raise AnnotationContractError("CALIBRATION_IDENTITY_ORDER_DRIFT")
    order = json.loads((root / "data/curation/papers/pilot1/publication_pilot1_pre_gate0_candidate_order.json").read_text(encoding="utf-8"))
    projection = {paper_id: [row["sourceUnitID"] for row in rows] for paper_id, rows in order["ordersByArtifact"].items()}
    if sum(map(len, projection.values())) != 215:
        raise AnnotationContractError("POST_CALIBRATION_CANDIDATE_CARDINALITY_MISMATCH")
    if canonical_json_hash(projection) != CANDIDATE_ID_ORDER_HASH:
        raise AnnotationContractError("POST_CALIBRATION_CANDIDATE_ORDER_DRIFT")
    inventory = _jsonl_index(
        root / "data/curation/papers/pilot1/publication_pilot1_source_unit_inventory.jsonl",
        omit_source_text=True,
    )
    source_manifest = json.loads(
        (root / "data/curation/papers/pilot1/publication_pilot1_source_unit_manifest.json").read_text(encoding="utf-8")
    )
    canonical_hashes = source_manifest.get("canonicalDocumentHashes", {})
    if not isinstance(canonical_hashes, Mapping):
        raise AnnotationContractError("ANNOTATION_CANONICAL_DOCUMENT_HASHES_INVALID")
    phase_nodes = _phase_b_nodes(root, str(source_manifest.get("phaseBArtifactHash", "")))
    for unit_id, unit in inventory.items():
        if unit.get("canonicalTextSha256") != canonical_hashes.get(str(unit.get("paperID"))):
            raise AnnotationContractError(f"ANNOTATION_CANONICAL_DOCUMENT_HASH_DRIFT:{unit_id}")
    resolve_deterministic_endpoints(inventory, tuple(inventory), phase_nodes)
    routing = _jsonl_index(root / "data/curation/papers/pilot1/publication_pilot1_unit_routing.jsonl")
    nodes, relations, expansions = _target_indexes(root)
    deferred_ids = {
        target_id for target_id, target in {**nodes, **relations}.items()
        if target["pilot_treatment"] == "deferred_resolution"
    }
    units: dict[str, Mapping[str, Any]] = dict(inventory)
    routes: dict[str, Mapping[str, Any]] = {}
    for unit_id in order_ids:
        unit, route = inventory.get(unit_id), routing.get(unit_id)
        if unit is None or route is None:
            raise AnnotationContractError(f"CALIBRATION_UNIT_BINDING_MISSING:{unit_id}")
        if route.get("routingStatus") != "routed":
            raise AnnotationContractError(f"CALIBRATION_STRUCTURALLY_BLOCKED_UNIT:{unit_id}")
        if unit["textHash"] != manifest["sourceUnitHashes"].get(unit_id) or route["sourceUnitTextHash"] != unit["textHash"]:
            raise AnnotationContractError(f"CALIBRATION_SOURCE_HASH_DRIFT:{unit_id}")
        validate_effective_route(route, unit, deferred_ids)
        routes[unit_id] = route
    for unit_id, route in routes.items():
        if set(route["eligibleNodeOperationalTargetIDs"]) - set(nodes):
            raise AnnotationContractError(f"CALIBRATION_EFFECTIVE_NODE_TARGET_UNKNOWN:{unit_id}")
        if set(route["eligibleRelationOperationalTargetIDs"]) - set(relations):
            raise AnnotationContractError(f"CALIBRATION_EFFECTIVE_RELATION_TARGET_UNKNOWN:{unit_id}")
    return AnnotationContracts(
        root, "calibration", units, routes, order_ids, nodes, relations, _display_index(root), expansions,
        hashes, dict(canonical_hashes), phase_nodes,
    )
