"""Deterministically extract HydroShare KG nodes and edges.

This script implements the contract in
``src/extraction/deterministic/hydroshare_extraction_mapping.md``. It reads the
HydroShare corpus JSON, applies only the deterministic node and edge mappings
listed there, and writes a rich interim JSON file with ``nodes`` and ``edges``
arrays. The output is regenerable and intentionally lives under ``data/interim``.

Inputs:
    data/interim/datasets/ciroh_hydroshare_corpus.json

Outputs:
    data/interim/datasets/hydroshare_nodes_edges.json

No network calls are made, no random identifiers are used, and re-running the
script with the same input produces byte-stable output.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import re
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import urlparse


PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_INPUT = PROJECT_ROOT / "data/interim/datasets/ciroh_hydroshare_corpus.json"
DEFAULT_OUTPUT = PROJECT_ROOT / "data/interim/datasets/hydroshare_nodes_edges.json"

EXTRACTION_METHOD = "deterministic"
CURATED = "curated"
REFERENCED = "referenced"

RESOURCE_TYPES = {"CompositeResource", "CollectionResource", "ToolResource"}
COMPOSITE = "CompositeResource"
COLLECTION = "CollectionResource"
TOOL = "ToolResource"

DERIVATION_PREDICATES = {
    "dcterms:isVersionOf",
    "dcterms:isFormatOf",
    "prov:wasDerivedFrom",
    "prov:wasRevisionOf",
}

REFERENCE_PREDICATES = {
    "dcterms:references",
    "dcterms:isReferencedBy",
    "dcterms:requires",
    "dcterms:source",
    "hsterms:isDescribedBy",
    "hsterms:isSimilarTo",
}

PERSON_IDENTIFIER_TYPES = {"ORCID", "GoogleScholarID", "ResearchGateID"}

HANDLED_TOP_LEVEL_FIELDS = {
    "abstract",
    "awards",
    "citation",
    "contributor_identifiers",
    "contributors",
    "creator_identifiers",
    "creators",
    "documentation",
    "files",
    "geospatial_relations",
    "hydroshare_links",
    "identifier",
    "language",
    "related_resources",
    "relations_from_meta",
    "resource_id",
    "resource_type",
    "rights",
    "spatial_coverage",
    "subjects",
    "temporal_coverage",
    "title",
    "tool_config",
    "typed_relations",
    "url",
}

DOI_RE = re.compile(r"(?:doi\.org/|doi:)?(10\.\d{4,9}/[^\s,;\"'<>]+)", re.IGNORECASE)
HYDROSHARE_RESOURCE_RE = re.compile(r"hydroshare\.org/resource/([0-9a-f]{32})", re.IGNORECASE)
ORCID_RE = re.compile(r"(\d{4}-\d{4}-\d{4}-\d{3}[\dX])", re.IGNORECASE)
ROR_RE = re.compile(r"ror\.org/([a-z0-9]{9})", re.IGNORECASE)


JsonDict = dict[str, Any]


@dataclass(frozen=True)
class Evidence:
    """EvidenceSpan payload attached to every emitted node and edge."""

    evidenceText: str
    sourceLocation: str
    extractionMethod: str
    sourceArtifact: str

    def to_dict(self) -> JsonDict:
        """Return a JSON-serializable evidence dictionary."""
        return {
            "evidenceText": self.evidenceText,
            "sourceLocation": self.sourceLocation,
            "extractionMethod": self.extractionMethod,
            "sourceArtifact": self.sourceArtifact,
        }


@dataclass
class Node:
    """A deterministic interim node record."""

    id: str
    class_name: str
    inventory_id: str
    attributes: JsonDict
    evidence: Evidence
    curation_status: str = CURATED

    def merge(self, other: "Node") -> None:
        """Merge missing attributes from another mention of the same node."""
        for key, value in other.attributes.items():
            if value in (None, "", [], {}):
                continue
            if key not in self.attributes or self.attributes[key] in (None, "", [], {}):
                self.attributes[key] = value
            elif self.attributes[key] != value:
                self._merge_conflicting_attribute(key, value)
        if self.curation_status == REFERENCED and other.curation_status == CURATED:
            self.curation_status = CURATED

    def _merge_conflicting_attribute(self, key: str, value: Any) -> None:
        """Keep conflicting deterministic attributes without overwriting evidence."""
        existing = self.attributes[key]
        if isinstance(existing, list):
            if value not in existing:
                existing.append(value)
                existing.sort(key=stable_json)
            return
        if existing != value:
            self.attributes[key] = sorted([existing, value], key=stable_json)

    def to_dict(self) -> JsonDict:
        """Return a JSON-serializable node dictionary."""
        return {
            "id": self.id,
            "class": self.class_name,
            "inventoryId": self.inventory_id,
            "attributes": sort_json(self.attributes),
            "evidence": self.evidence.to_dict(),
            "curationStatus": self.curation_status,
        }


@dataclass
class Edge:
    """A deterministic interim edge record."""

    id: str
    relation: str
    inventory_id: str
    source: str
    target: str
    evidence: Evidence
    attributes: JsonDict = field(default_factory=dict)

    def to_dict(self) -> JsonDict:
        """Return a JSON-serializable edge dictionary."""
        payload: JsonDict = {
            "id": self.id,
            "relation": self.relation,
            "inventoryId": self.inventory_id,
            "source": self.source,
            "target": self.target,
            "evidence": self.evidence.to_dict(),
        }
        if self.attributes:
            payload["attributes"] = sort_json(self.attributes)
        return payload


class GraphBuilder:
    """Accumulates deterministic nodes, edges, and skipped-field diagnostics."""

    def __init__(self, resources_by_id: dict[str, JsonDict]) -> None:
        """Create a graph builder scoped to the known HydroShare resources."""
        self.resources_by_id = resources_by_id
        self.corpus_ids = set(resources_by_id)
        self.nodes: dict[str, Node] = {}
        self.edges: dict[str, Edge] = {}
        self.skipped: Counter[str] = Counter()

    def add_node(
        self,
        node_id: str,
        class_name: str,
        inventory_id: str,
        attributes: JsonDict,
        evidence: Evidence,
        curation_status: str = CURATED,
    ) -> str:
        """Add or merge a node and return its deterministic ID."""
        node = Node(
            id=node_id,
            class_name=class_name,
            inventory_id=inventory_id,
            attributes=clean_dict(attributes),
            evidence=evidence,
            curation_status=curation_status,
        )
        if node_id in self.nodes:
            self.nodes[node_id].merge(node)
        else:
            self.nodes[node_id] = node
        return node_id

    def add_edge(
        self,
        relation: str,
        inventory_id: str,
        source: str,
        target: str,
        evidence: Evidence,
        attributes: JsonDict | None = None,
    ) -> str:
        """Add an edge, deduplicating by semantic source/relation/target key."""
        edge_id = make_edge_id(source, relation, target, inventory_id)
        if edge_id not in self.edges:
            self.edges[edge_id] = Edge(
                id=edge_id,
                relation=relation,
                inventory_id=inventory_id,
                source=source,
                target=target,
                evidence=evidence,
                attributes=clean_dict(attributes or {}),
            )
        return edge_id

    def skip(self, reason: str) -> None:
        """Record a skipped field, predicate, or ambiguous mapping."""
        self.skipped[reason] += 1

    def to_output(self) -> JsonDict:
        """Return deterministic output with sorted nodes and edges."""
        return {
            "nodes": [self.nodes[node_id].to_dict() for node_id in sorted(self.nodes)],
            "edges": [self.edges[edge_id].to_dict() for edge_id in sorted(self.edges)],
        }


def stable_json(value: Any) -> str:
    """Serialize a value deterministically for sorting and hashing."""
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def sort_json(value: Any) -> Any:
    """Recursively sort dictionaries and lists for byte-stable JSON output."""
    if isinstance(value, dict):
        return {key: sort_json(value[key]) for key in sorted(value)}
    if isinstance(value, list):
        return [sort_json(item) for item in value]
    return value


def clean_dict(value: JsonDict) -> JsonDict:
    """Remove empty attributes while preserving meaningful falsey values."""
    return {
        key: val
        for key, val in value.items()
        if val is not None and val != "" and val != [] and val != {}
    }


def slugify(value: str) -> str:
    """Normalize text into a deterministic, compact key fragment."""
    normalized = value.strip().lower()
    normalized = re.sub(r"https?://", "", normalized)
    normalized = re.sub(r"[^a-z0-9]+", "-", normalized)
    return normalized.strip("-") or "unknown"


def short_hash(value: str, length: int = 16) -> str:
    """Return a stable short SHA-256 hash."""
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:length]


def make_edge_id(source: str, relation: str, target: str, inventory_id: str) -> str:
    """Create a deterministic edge ID from its semantic assertion."""
    key = stable_json(
        {"source": source, "relation": relation, "target": target, "inventoryId": inventory_id}
    )
    return f"edge:{short_hash(key, 20)}"


def stringify_evidence(value: Any) -> str:
    """Convert an evidence value into stable non-empty text."""
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    return json.dumps(value, sort_keys=True, ensure_ascii=False)


def make_evidence(resource_id: str, value: Any, json_path: str) -> Evidence:
    """Build an EvidenceSpan for a HydroShare JSON value."""
    return Evidence(
        evidenceText=stringify_evidence(value),
        sourceLocation=f"{resource_id}:{json_path}",
        extractionMethod=EXTRACTION_METHOD,
        sourceArtifact=f"hydroshare:{resource_id}",
    )


def normalize_orcid(value: str | None) -> str | None:
    """Extract and normalize an ORCID identifier from a URL or raw string."""
    if not value:
        return None
    match = ORCID_RE.search(value)
    return match.group(1).upper() if match else None


def normalize_ror(value: str | None) -> str | None:
    """Extract and normalize a ROR identifier from a URL."""
    if not value:
        return None
    match = ROR_RE.search(value)
    return match.group(1).lower() if match else None


def normalize_doi(value: str | None) -> str | None:
    """Extract and normalize a DOI from text or URL."""
    if not value:
        return None
    match = DOI_RE.search(value)
    if not match:
        return None
    return match.group(1).rstrip(".").lower()


def extract_hydroshare_resource_id(value: str | None) -> str | None:
    """Extract a HydroShare resource ID from a target string or URL."""
    if not value:
        return None
    match = HYDROSHARE_RESOURCE_RE.search(value)
    return match.group(1).lower() if match else None


def first_url(values: Iterable[str | None]) -> str | None:
    """Return the first non-empty URL-like string from an iterable."""
    for value in values:
        if value and re.match(r"https?://", value):
            return value
    return None


def is_repository_url(url: str) -> bool:
    """Return whether a URL clearly identifies a code repository."""
    host = urlparse(url).netloc.lower()
    return any(domain in host for domain in ("github.com", "gitlab.com", "bitbucket.org"))


def license_id(rights: JsonDict) -> str:
    """Create the deterministic License node ID."""
    url = rights.get("url")
    statement = rights.get("statement")
    spdx_id = spdx_from_rights_url(url)
    if spdx_id:
        return f"license:{spdx_id.lower()}"
    if url:
        return f"license:url:{slugify(url)}"
    return f"license:name:{slugify(statement or 'unknown-license')}"


def spdx_from_rights_url(url: str | None) -> str | None:
    """Resolve common HydroShare license URLs to SPDX-like identifiers."""
    if not url:
        return None
    lower = url.lower().rstrip("/")
    if "creativecommons.org/licenses/by/4.0" in lower:
        return "CC-BY-4.0"
    return None


def person_identifier_index(identifiers: list[JsonDict]) -> dict[str, list[JsonDict]]:
    """Index flattened person identifiers by the source person name."""
    by_name: dict[str, list[JsonDict]] = defaultdict(list)
    for item in identifiers:
        name = item.get("person_name")
        if name:
            by_name[name].append(item)
    return by_name


def best_person_key(person: JsonDict, extra_identifiers: list[JsonDict]) -> tuple[str, str, str | None]:
    """Return the deterministic Person ID, identifier regime, and ORCID."""
    all_identifiers = list(person.get("identifiers") or []) + extra_identifiers
    for identifier in all_identifiers:
        if identifier.get("id_type") == "ORCID":
            orcid = normalize_orcid(identifier.get("url"))
            if orcid:
                return f"person:orcid:{orcid}", "ORCID", orcid
    name = person.get("name") or "unknown-person"
    return f"person:name:{slugify(name)}", "name-key", None


def organization_id(name: str, url: str | None = None) -> tuple[str, str, str | None]:
    """Return the deterministic Organization ID, identifier regime, and ROR."""
    ror = normalize_ror(url)
    if ror:
        return f"organization:ror:{ror}", "ROR", ror
    return f"organization:name:{slugify(name)}", "name-key", None


def identifier_node_id(identifier: str) -> str:
    """Return a deterministic Identifier node ID."""
    return f"identifier:{slugify(identifier)}"


def award_node_id(award: JsonDict) -> str:
    """Return a deterministic Award node ID from agency and award number."""
    agency = award.get("funding_agency_name") or "unknown-agency"
    number = award.get("number") or award.get("title") or "unknown-award"
    return f"award:{slugify(agency)}:{slugify(number)}"


def subject_node_id(subject: str) -> str:
    """Return a deterministic Subject node ID."""
    return f"subject:{slugify(subject)}"


def file_node_id(resource_id: str, file_entry: JsonDict) -> str:
    """Return a deterministic DatasetFile node ID scoped to its resource."""
    file_key = file_entry.get("file_path") or file_entry.get("file_name") or stable_json(file_entry)
    return f"{resource_id}:file:{slugify(file_key)}"


def tool_node_id(url: str, title: str | None) -> str:
    """Return a deterministic Tool node ID from launch URL or title."""
    if url:
        parsed = urlparse(url)
        host = parsed.netloc or url
        return f"tool:url:{slugify(host)}"
    return f"tool:name:{slugify(title or 'unknown-tool')}"


def relation_target_text(entry: JsonDict) -> str:
    """Return the preferred human-readable relation target text."""
    return stringify_evidence(entry.get("target") or entry)


def relation_embedded_urls(entry: JsonDict) -> list[str]:
    """Return relation embedded URLs, falling back to the target when it is a URL."""
    urls = list(entry.get("embedded_urls") or [])
    target = entry.get("target")
    if isinstance(target, str) and re.match(r"https?://", target) and target not in urls:
        urls.insert(0, target)
    return urls


def load_corpus(path: Path) -> list[JsonDict]:
    """Load the HydroShare corpus as a list of resource dictionaries."""
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        return list(data.values())
    raise ValueError(f"Expected list or dict corpus at {path}, found {type(data).__name__}")


def extract_dataset_resource(resource: JsonDict, builder: GraphBuilder) -> None:
    """Apply N1, N2, and E1 for the HydroShare resource itself."""
    resource_id = require_resource_id(resource)
    resource_type = resource.get("resource_type")
    title = resource.get("title")
    abstract = resource.get("abstract")

    builder.add_node(
        resource_id,
        "DatasetResource",
        "A-D01",
        {
            "resourceId": resource_id,
            "resourceType": resource_type,
            "title": title,
            "citation": resource.get("citation"),
            "abstract": abstract,
            "documentation": resource.get("documentation"),
            "language": resource.get("language"),
            "identifier": resource.get("identifier"),
            "url": resource.get("url"),
        },
        make_evidence(resource_id, {"title": title, "abstract": abstract}, "$"),
        CURATED,
    )

    if resource_type:
        type_id = f"resource-type:{slugify(resource_type)}"
        builder.add_node(
            type_id,
            "ResourceType",
            "A-D02",
            {"label": resource_type},
            make_evidence(resource_id, resource_type, "resource_type"),
            CURATED,
        )
        builder.add_edge(
            "hasResourceType",
            "C-D01",
            resource_id,
            type_id,
            make_evidence(resource_id, resource_type, "resource_type"),
        )
    else:
        builder.skip("missing:resource_type")


def extract_agents(resource: JsonDict, builder: GraphBuilder) -> None:
    """Apply N3-N5, N11b, E3, E4, E6, and E13 for people and affiliations."""
    resource_id = require_resource_id(resource)
    creator_ids = person_identifier_index(resource.get("creator_identifiers") or [])
    contributor_ids = person_identifier_index(resource.get("contributor_identifiers") or [])

    for group_name, relation, inventory_id, people, id_index in (
        ("creators", "hasCreator", "C-D03", resource.get("creators") or [], creator_ids),
        (
            "contributors",
            "hasContributor",
            "C-DC05/A-AG",
            resource.get("contributors") or [],
            contributor_ids,
        ),
    ):
        for index, person in enumerate(people):
            path = f"{group_name}[{index}]"
            person_id = add_person(resource_id, person, id_index.get(person.get("name"), []), path, builder)
            edge_attrs = {}
            if group_name == "creators" and person.get("creator_order") is not None:
                edge_attrs["creatorOrder"] = person.get("creator_order")
            builder.add_edge(
                relation,
                inventory_id,
                resource_id,
                person_id,
                make_evidence(resource_id, person.get("name"), path),
                edge_attrs,
            )

            organization = person.get("organization")
            if organization:
                org_id, regime, ror = organization_id(organization)
                builder.add_node(
                    org_id,
                    "Organization",
                    "A-AG02",
                    {
                        "name": organization,
                        "identifierRegime": regime,
                        "ror": ror,
                    },
                    make_evidence(resource_id, organization, f"{path}.organization"),
                    CURATED,
                )
                builder.add_edge(
                    "affiliatedWith",
                    "A-AG-R1",
                    person_id,
                    org_id,
                    make_evidence(resource_id, organization, f"{path}.organization"),
                )

    add_person_identifier_edges(resource_id, "creator_identifiers", resource.get("creator_identifiers") or [], creator_ids, builder)
    add_person_identifier_edges(
        resource_id,
        "contributor_identifiers",
        resource.get("contributor_identifiers") or [],
        contributor_ids,
        builder,
    )


def add_person(
    resource_id: str,
    person: JsonDict,
    extra_identifiers: list[JsonDict],
    path: str,
    builder: GraphBuilder,
) -> str:
    """Add a Person node seeded with its best deterministic key."""
    person_id, regime, orcid = best_person_key(person, extra_identifiers)
    identifiers_by_value = {
        stable_json(identifier): identifier
        for item in list(person.get("identifiers") or []) + extra_identifiers
        if item.get("url")
        for identifier in [
            clean_dict({"idType": item.get("id_type"), "url": item.get("url")})
        ]
    }
    identifiers = [identifiers_by_value[key] for key in sorted(identifiers_by_value)]
    builder.add_node(
        person_id,
        "Person",
        "A-AG01",
        {
            "name": person.get("name"),
            "hydroshareUserId": person.get("hydroshare_user_id"),
            "identifierRegime": regime,
            "orcid": orcid,
            "identifiers": identifiers,
        },
        make_evidence(resource_id, person.get("name"), path),
        CURATED,
    )
    return person_id


def add_person_identifier_edges(
    resource_id: str,
    field_name: str,
    identifiers: list[JsonDict],
    identifier_index: dict[str, list[JsonDict]],
    builder: GraphBuilder,
) -> None:
    """Add supported Identifier nodes and Person-hasIdentifier edges."""
    for index, item in enumerate(identifiers):
        path = f"{field_name}[{index}]"
        identifier_type = item.get("id_type")
        if identifier_type not in PERSON_IDENTIFIER_TYPES:
            builder.skip(f"unmapped_person_identifier:{item.get('id_type') or 'unknown'}")
            continue
        identifier_value = item.get("url")
        if not identifier_value:
            builder.skip(f"invalid_person_identifier:{identifier_type}")
            continue
        normalized_value = normalize_orcid(identifier_value) if identifier_type == "ORCID" else None
        if identifier_type == "ORCID" and not normalized_value:
            builder.skip("invalid_orcid_identifier")
            continue
        person_name = item.get("person_name")
        person_id = None
        for node_id, node in builder.nodes.items():
            if node.class_name == "Person" and node.attributes.get("name") == person_name:
                person_id = node_id
                break
        if not person_id:
            person_id, _, _ = best_person_key({"name": person_name}, identifier_index.get(person_name, []))
        identifier_id = identifier_node_id(identifier_value)
        builder.add_node(
            identifier_id,
            "Identifier",
            "A-ID01",
            {
                "identifierValue": identifier_value,
                "identifierType": identifier_type,
                "normalizedValue": normalized_value,
            },
            make_evidence(resource_id, identifier_value, path),
            CURATED,
        )
        builder.add_edge(
            "hasIdentifier",
            "A-ID01 (ID-R1)",
            person_id,
            identifier_id,
            make_evidence(resource_id, identifier_value, path),
        )


def extract_metadata_nodes(resource: JsonDict, builder: GraphBuilder) -> None:
    """Apply N6-N12 and E5-E11 for dataset metadata."""
    resource_id = require_resource_id(resource)
    extract_resource_identifiers(resource, builder)
    extract_license(resource, builder)
    extract_subjects(resource, builder)
    extract_spatial_coverage(resource, builder)
    extract_temporal_coverage(resource, builder)
    extract_awards(resource, builder)


def extract_resource_identifiers(resource: JsonDict, builder: GraphBuilder) -> None:
    """Apply N12 and E5 for the resource identifier and URL fields."""
    resource_id = require_resource_id(resource)
    seen: set[str] = set()
    for field_name in ("identifier", "url"):
        identifier_value = resource.get(field_name)
        if not identifier_value or identifier_value in seen:
            continue
        seen.add(identifier_value)
        identifier_id = identifier_node_id(identifier_value)
        builder.add_node(
            identifier_id,
            "Identifier",
            "A-ID01",
            {"identifierValue": identifier_value, "identifierType": "URL"},
            make_evidence(resource_id, identifier_value, field_name),
            CURATED,
        )
        builder.add_edge(
            "hasIdentifier",
            "C-D04",
            resource_id,
            identifier_id,
            make_evidence(resource_id, identifier_value, field_name),
        )


def extract_license(resource: JsonDict, builder: GraphBuilder) -> None:
    """Apply N6 and E7 for HydroShare rights metadata."""
    resource_id = require_resource_id(resource)
    rights = resource.get("rights") or {}
    if not rights:
        return
    node_id = license_id(rights)
    statement = rights.get("statement")
    url = rights.get("url")
    builder.add_node(
        node_id,
        "License",
        "A-D05",
        {"statement": statement, "url": url, "spdxId": spdx_from_rights_url(url)},
        make_evidence(resource_id, statement or url, "rights"),
        CURATED,
    )
    builder.add_edge(
        "hasLicense",
        "C-D05",
        resource_id,
        node_id,
        make_evidence(resource_id, statement or url, "rights"),
    )


def extract_subjects(resource: JsonDict, builder: GraphBuilder) -> None:
    """Apply N7 and E8 for subjects."""
    resource_id = require_resource_id(resource)
    for index, subject in enumerate(resource.get("subjects") or []):
        node_id = subject_node_id(subject)
        path = f"subjects[{index}]"
        builder.add_node(
            node_id,
            "Subject",
            "A-D06",
            {"label": subject},
            make_evidence(resource_id, subject, path),
            CURATED,
        )
        builder.add_edge(
            "hasSubject",
            "C-D06",
            resource_id,
            node_id,
            make_evidence(resource_id, subject, path),
        )


def extract_spatial_coverage(resource: JsonDict, builder: GraphBuilder) -> None:
    """Apply N8 and E9 for spatial coverage."""
    resource_id = require_resource_id(resource)
    coverage = resource.get("spatial_coverage")
    if not coverage:
        return
    node_id = f"{resource_id}:spatial"
    builder.add_node(
        node_id,
        "SpatialCoverage",
        "A-D07→A-DOM09",
        dict(coverage),
        make_evidence(resource_id, coverage, "spatial_coverage"),
        CURATED,
    )
    builder.add_edge(
        "hasSpatialCoverage",
        "C-D07",
        resource_id,
        node_id,
        make_evidence(resource_id, coverage, "spatial_coverage"),
    )


def extract_temporal_coverage(resource: JsonDict, builder: GraphBuilder) -> None:
    """Apply N9 and E10 for temporal coverage."""
    resource_id = require_resource_id(resource)
    coverage = resource.get("temporal_coverage")
    if not coverage:
        return
    node_id = f"{resource_id}:temporal"
    builder.add_node(
        node_id,
        "TemporalCoverage",
        "A-D08→A-DOM10",
        dict(coverage),
        make_evidence(resource_id, coverage, "temporal_coverage"),
        CURATED,
    )
    builder.add_edge(
        "coversPeriod",
        "C-D08",
        resource_id,
        node_id,
        make_evidence(resource_id, coverage, "temporal_coverage"),
    )


def extract_awards(resource: JsonDict, builder: GraphBuilder) -> None:
    """Apply N10, N11, E11, and E12 for funding awards and agencies."""
    resource_id = require_resource_id(resource)
    for index, award in enumerate(resource.get("awards") or []):
        path = f"awards[{index}]"
        award_id = award_node_id(award)
        award_text = award.get("title") or award.get("number") or award
        builder.add_node(
            award_id,
            "Award",
            "A-D09",
            {
                "title": award.get("title"),
                "number": award.get("number"),
                "fundingAgencyName": award.get("funding_agency_name"),
                "fundingAgencyUrl": award.get("funding_agency_url"),
            },
            make_evidence(resource_id, award_text, path),
            CURATED,
        )
        builder.add_edge(
            "fundedBy",
            "C-D09 / A-AG-R2",
            resource_id,
            award_id,
            make_evidence(resource_id, award_text, path),
        )

        agency = award.get("funding_agency_name")
        if agency:
            org_id, regime, ror = organization_id(agency, award.get("funding_agency_url"))
            agency_path = f"{path}.funding_agency_name"
            builder.add_node(
                org_id,
                "Organization",
                "A-AG02",
                {
                    "name": agency,
                    "identifierRegime": regime,
                    "ror": ror,
                    "url": award.get("funding_agency_url"),
                },
                make_evidence(resource_id, agency, agency_path),
                CURATED,
            )
            builder.add_edge(
                "fundedBy",
                "A-AG-R2",
                award_id,
                org_id,
                make_evidence(resource_id, agency, agency_path),
            )


def extract_files(resource: JsonDict, builder: GraphBuilder) -> None:
    """Apply Composite-only N13 and E2 for files."""
    resource_id = require_resource_id(resource)
    if resource.get("resource_type") != COMPOSITE:
        if resource.get("files"):
            builder.skip(f"unexpected_files_for_type:{resource.get('resource_type')}")
        return
    for index, file_entry in enumerate(resource.get("files") or []):
        path = f"files[{index}]"
        node_id = file_node_id(resource_id, file_entry)
        file_name = file_entry.get("file_name")
        builder.add_node(
            node_id,
            "DatasetFile",
            "A-D03",
            {
                "fileName": file_name,
                "filePath": file_entry.get("file_path"),
                "extension": file_entry.get("extension"),
                "checksum": file_entry.get("checksum"),
            },
            make_evidence(resource_id, file_name or file_entry, path),
            CURATED,
        )
        builder.add_edge(
            "hasFile",
            "C-D02",
            resource_id,
            node_id,
            make_evidence(resource_id, file_name or file_entry, path),
        )


def extract_tool_configuration(resource: JsonDict, builder: GraphBuilder) -> None:
    """Apply Tool-only N14-N16 and E14-E15."""
    resource_id = require_resource_id(resource)
    tool_config = resource.get("tool_config")
    if resource.get("resource_type") != TOOL:
        if tool_config:
            builder.skip(f"unexpected_tool_config_for_type:{resource.get('resource_type')}")
        return
    if not tool_config:
        return

    descriptor = tool_descriptor(resource)
    config_id = f"{resource_id}:tool-config"
    launch_url = tool_config.get("app_home_page_url")
    builder.add_node(
        config_id,
        "ToolConfiguration",
        "A-D10",
        {
            "descriptor": descriptor,
            "launchURL": launch_url,
            "requestUrlBase": tool_config.get("request_url_base"),
            "requestUrlBaseFile": tool_config.get("request_url_base_file"),
            "toolVersion": tool_config.get("tool_version"),
            "testingProtocolUrl": tool_config.get("testing_protocol_url"),
            "toolIconUrl": tool_config.get("tool_icon_url"),
            "supportedFileExtensions": tool_config.get("supported_file_extensions"),
            "supportedResourceTypes": tool_config.get("supported_resource_types"),
            "supportedSharingStatus": tool_config.get("supported_sharing_status"),
        },
        make_evidence(resource_id, descriptor, "tool_config"),
        CURATED,
    )
    builder.add_edge(
        "hasToolConfig",
        "C-D10",
        resource_id,
        config_id,
        make_evidence(resource_id, descriptor, "tool_config"),
    )

    if launch_url:
        tool_id = tool_node_id(launch_url, resource.get("title"))
        parsed = urlparse(launch_url)
        builder.add_node(
            tool_id,
            "Tool",
            "A-DOM02",
            {
                "name": resource.get("title") or parsed.netloc,
                "launchURL": launch_url,
                "host": parsed.netloc,
            },
            make_evidence(resource_id, launch_url, "tool_config.app_home_page_url"),
            CURATED,
        )
        builder.add_edge(
            "launchesApp",
            "C-D11",
            config_id,
            tool_id,
            make_evidence(resource_id, launch_url, "tool_config.app_home_page_url"),
        )


def tool_descriptor(resource: JsonDict) -> str:
    """Create a deterministic descriptor for a ToolConfiguration."""
    tool_config = resource.get("tool_config") or {}
    title = resource.get("title") or "HydroShare tool"
    version = tool_config.get("tool_version")
    if version:
        return f"{title}, v{version}"
    return title


def extract_relations(resource: JsonDict, builder: GraphBuilder) -> None:
    """Apply E16-E21 for HydroShare relation fields."""
    extract_collection_members(resource, builder)
    extract_memberships(resource, builder)
    extract_derivations(resource, builder)
    extract_references(resource, builder)
    extract_geospatial_relations(resource, builder)
    extract_execution_relations(resource, builder)


def extract_collection_members(resource: JsonDict, builder: GraphBuilder) -> None:
    """Apply Collection-only E16 for dcterms:hasPart member relations."""
    resource_id = require_resource_id(resource)
    if resource.get("resource_type") != COLLECTION:
        return
    for field_name, index, entry in iter_relation_entries(resource, ("hydroshare_links", "typed_relations")):
        if entry.get("predicate_qname") != "dcterms:hasPart":
            continue
        target_id = resolve_dataset_resource_target(resource_id, entry, f"{field_name}[{index}]", builder)
        if not target_id:
            builder.skip("unresolved_hasMember_target")
            continue
        builder.add_edge(
            "hasMember",
            "C-D12",
            resource_id,
            target_id,
            make_evidence(resource_id, relation_target_text(entry), f"{field_name}[{index}]"),
            {"predicateQName": entry.get("predicate_qname")},
        )


def extract_memberships(resource: JsonDict, builder: GraphBuilder) -> None:
    """Apply E17 for dcterms:isPartOf membership relations."""
    resource_id = require_resource_id(resource)
    for field_name, index, entry in iter_relation_entries(resource, ("hydroshare_links", "typed_relations")):
        if entry.get("predicate_qname") != "dcterms:isPartOf":
            continue
        target_id = resolve_dataset_resource_target(resource_id, entry, f"{field_name}[{index}]", builder)
        if not target_id:
            builder.skip("unresolved_isMemberOf_target")
            continue
        builder.add_edge(
            "isMemberOf",
            "C-D13",
            resource_id,
            target_id,
            make_evidence(resource_id, relation_target_text(entry), f"{field_name}[{index}]"),
            {"predicateQName": entry.get("predicate_qname")},
        )


def extract_derivations(resource: JsonDict, builder: GraphBuilder) -> None:
    """Apply E18 for deterministic derivation/version predicates."""
    resource_id = require_resource_id(resource)
    for field_name, index, entry in iter_relation_entries(resource, ("typed_relations", "hydroshare_links")):
        predicate = entry.get("predicate_qname")
        if predicate not in DERIVATION_PREDICATES:
            continue
        target_id = resolve_dataset_resource_target(resource_id, entry, f"{field_name}[{index}]", builder)
        if not target_id:
            builder.skip(f"unresolved_derivedFrom_target:{predicate}")
            continue
        builder.add_edge(
            "derivedFrom",
            "C-D14",
            resource_id,
            target_id,
            make_evidence(resource_id, relation_target_text(entry), f"{field_name}[{index}]"),
            {"predicateQName": predicate},
        )


def extract_references(resource: JsonDict, builder: GraphBuilder) -> None:
    """Apply E19 for deterministic DOI/URL references to paper/repo/dataset targets."""
    resource_id = require_resource_id(resource)
    for field_name, index, entry in iter_relation_entries(resource, ("related_resources", "typed_relations")):
        predicate = entry.get("predicate_qname")
        if predicate not in REFERENCE_PREDICATES:
            continue
        target_id = resolve_reference_target(resource_id, entry, f"{field_name}[{index}]", builder)
        if not target_id:
            builder.skip(f"deferred_to_llm:reference_target:{predicate}")
            continue
        builder.add_edge(
            "references",
            "C-D19",
            resource_id,
            target_id,
            make_evidence(resource_id, relation_target_text(entry), f"{field_name}[{index}]"),
            {"predicateQName": predicate},
        )


def extract_geospatial_relations(resource: JsonDict, builder: GraphBuilder) -> None:
    """Apply E20 for geoconnex hydrologic feature references."""
    resource_id = require_resource_id(resource)
    for index, entry in enumerate(resource.get("geospatial_relations") or []):
        path = f"geospatial_relations[{index}]"
        target = entry.get("target") or first_url(relation_embedded_urls(entry))
        if not target:
            builder.skip("unresolved_geospatial_target")
            continue
        node_id = f"hydrologic-feature:{slugify(target)}"
        builder.add_node(
            node_id,
            "HydrologicFeature",
            "A-DOM07",
            {
                "identifierValue": target,
                "name": entry.get("name"),
                "identifierRegime": "geoconnex-url",
            },
            make_evidence(resource_id, entry.get("name") or target, path),
            REFERENCED,
        )
        builder.add_edge(
            "referencesFeature",
            "C-D15",
            resource_id,
            node_id,
            make_evidence(resource_id, entry.get("name") or target, path),
            {"predicateQName": entry.get("predicate_qname")},
        )


def extract_execution_relations(resource: JsonDict, builder: GraphBuilder) -> None:
    """Apply E21 for hsterms:isExecutedBy relations."""
    resource_id = require_resource_id(resource)
    relation_fields = (
        "typed_relations",
        "related_resources",
        "relations_from_meta",
        "hydroshare_links",
    )
    for field_name, index, entry in iter_relation_entries(resource, relation_fields):
        if relation_predicate(entry) != "hsterms:isExecutedBy":
            continue
        path = f"{field_name}[{index}]"
        target_id = resolve_tool_target(resource_id, entry, path, builder)
        if not target_id:
            builder.skip("deferred_to_llm:isExecutedBy_target")
            continue
        builder.add_edge(
            "isExecutedBy",
            "C-D20",
            resource_id,
            target_id,
            make_evidence(resource_id, relation_target_text(entry), path),
            {"predicateQName": "hsterms:isExecutedBy"},
        )


def relation_predicate(entry: JsonDict) -> str | None:
    """Return the relation predicate, including known metadata-label equivalents."""
    predicate = entry.get("predicate_qname")
    if predicate:
        return predicate
    relation_label = (entry.get("relation_label") or "").strip().lower()
    if relation_label == "the content of this resource can be executed by":
        return "hsterms:isExecutedBy"
    return None


def iter_relation_entries(resource: JsonDict, field_names: tuple[str, ...]) -> Iterable[tuple[str, int, JsonDict]]:
    """Yield relation entries once per semantic predicate/target combination."""
    seen: set[tuple[str | None, str | None, str | None]] = set()
    for field_name in field_names:
        for index, entry in enumerate(resource.get(field_name) or []):
            predicate = relation_predicate(entry)
            key = (
                predicate,
                entry.get("target_resource_id"),
                entry.get("target"),
            )
            if key in seen:
                continue
            seen.add(key)
            if predicate and not entry.get("predicate_qname"):
                entry = dict(entry)
                entry["predicate_qname"] = predicate
            yield field_name, index, entry


def resolve_dataset_resource_target(
    source_resource_id: str,
    entry: JsonDict,
    path: str,
    builder: GraphBuilder,
) -> str | None:
    """Resolve or stub a DatasetResource target from a relation entry."""
    target_id = entry.get("target_resource_id") or extract_hydroshare_resource_id(entry.get("target"))
    if not target_id:
        for url in relation_embedded_urls(entry):
            target_id = extract_hydroshare_resource_id(url)
            if target_id:
                break
    if not target_id:
        return None
    target_text = relation_target_text(entry)
    curation_status = CURATED if target_id in builder.corpus_ids else REFERENCED
    builder.add_node(
        target_id,
        "DatasetResource",
        "A-D01",
        {
            "resourceId": target_id,
            "identifierRegime": "hydroshare-resource-id",
            "citation": target_text,
        },
        make_evidence(source_resource_id, target_text, path),
        curation_status,
    )
    return target_id


def resolve_reference_target(
    source_resource_id: str,
    entry: JsonDict,
    path: str,
    builder: GraphBuilder,
) -> str | None:
    """Resolve or stub an E19 reference target by deterministic identifier kind."""
    dataset_target = resolve_dataset_resource_target(source_resource_id, entry, path, builder)
    if dataset_target:
        return dataset_target

    target_text = relation_target_text(entry)
    doi = normalize_doi(target_text)
    if doi:
        return add_paper_stub(source_resource_id, doi, target_text, path, builder)

    for url in relation_embedded_urls(entry):
        doi = normalize_doi(url)
        if doi:
            return add_paper_stub(source_resource_id, doi, target_text or url, path, builder)
        if is_repository_url(url):
            return add_repository_stub(source_resource_id, url, target_text or url, path, builder)
        return add_external_dataset_stub(source_resource_id, url, target_text or url, path, builder)

    if entry.get("predicate_qname") == "hsterms:isDescribedBy" and target_text:
        return add_citation_text_paper_stub(source_resource_id, target_text, path, builder)

    return None


def resolve_tool_target(
    source_resource_id: str,
    entry: JsonDict,
    path: str,
    builder: GraphBuilder,
) -> str | None:
    """Resolve an isExecutedBy target to a Tool entity or referenced Tool stub."""
    target_resource_id = entry.get("target_resource_id")
    if not target_resource_id:
        target_resource_id = extract_hydroshare_resource_id(entry.get("target"))
    if target_resource_id:
        target_resource = builder.resources_by_id.get(target_resource_id)
        if target_resource and target_resource.get("resource_type") == TOOL:
            tool_config = target_resource.get("tool_config") or {}
            launch_url = tool_config.get("app_home_page_url") or ""
            node_id = tool_node_id(launch_url, target_resource.get("title"))
            builder.add_node(
                node_id,
                "Tool",
                "A-DOM02",
                {
                    "name": target_resource.get("title"),
                    "launchURL": launch_url,
                    "host": urlparse(launch_url).netloc if launch_url else None,
                    "hydroshareResourceId": target_resource_id,
                    "identifierRegime": "hydroshare-tool-resource",
                },
                make_evidence(
                    target_resource_id,
                    launch_url or target_resource.get("title"),
                    "tool_config.app_home_page_url" if launch_url else "title",
                ),
                CURATED,
            )
            return node_id

        node_id = f"tool:hydroshare:{target_resource_id}"
        builder.add_node(
            node_id,
            "Tool",
            "A-DOM02",
            {
                "name": relation_target_text(entry),
                "hydroshareResourceId": target_resource_id,
                "identifierRegime": "hydroshare-resource-id",
            },
            make_evidence(source_resource_id, relation_target_text(entry), path),
            CURATED if target_resource_id in builder.corpus_ids else REFERENCED,
        )
        return node_id

    for url in relation_embedded_urls(entry):
        parsed = urlparse(url)
        node_id = f"tool:url:{short_hash(url, 20)}"
        builder.add_node(
            node_id,
            "Tool",
            "A-DOM02",
            {
                "name": relation_target_text(entry),
                "url": url,
                "host": parsed.netloc,
                "identifierRegime": "external-url",
            },
            make_evidence(source_resource_id, relation_target_text(entry) or url, path),
            REFERENCED,
        )
        return node_id

    return None


def add_paper_stub(
    source_resource_id: str,
    doi: str,
    target_text: str,
    path: str,
    builder: GraphBuilder,
) -> str:
    """Emit a referenced Paper stub for a DOI target."""
    node_id = f"paper:doi:{slugify(doi)}"
    builder.add_node(
        node_id,
        "Paper",
        "A-P01",
        {
            "identifierRegime": "DOI",
            "doi": doi,
            "citation": target_text,
        },
        make_evidence(source_resource_id, target_text or doi, path),
        REFERENCED,
    )
    return node_id


def add_external_dataset_stub(
    source_resource_id: str,
    url: str,
    target_text: str,
    path: str,
    builder: GraphBuilder,
) -> str:
    """Emit a referenced DatasetResource stub for a generic external URL."""
    parsed = urlparse(url)
    node_id = f"dataset:url:{short_hash(url, 20)}"
    builder.add_node(
        node_id,
        "DatasetResource",
        "A-D01",
        {
            "identifierRegime": "external-url",
            "url": url,
            "host": parsed.netloc,
            "citation": target_text,
        },
        make_evidence(source_resource_id, target_text or url, path),
        REFERENCED,
    )
    return node_id


def add_citation_text_paper_stub(
    source_resource_id: str,
    target_text: str,
    path: str,
    builder: GraphBuilder,
) -> str:
    """Emit a referenced Paper stub for a describing publication citation."""
    node_id = f"paper:citation:{short_hash(target_text, 20)}"
    builder.add_node(
        node_id,
        "Paper",
        "A-P01",
        {
            "identifierRegime": "citation-text",
            "citation": target_text,
        },
        make_evidence(source_resource_id, target_text, path),
        REFERENCED,
    )
    return node_id


def add_repository_stub(
    source_resource_id: str,
    url: str,
    target_text: str,
    path: str,
    builder: GraphBuilder,
) -> str:
    """Emit a referenced Repository stub for a code repository URL."""
    parsed = urlparse(url)
    repo_path = parsed.path.strip("/")
    node_id = f"repository:url:{slugify(parsed.netloc + '/' + repo_path)}"
    builder.add_node(
        node_id,
        "Repository",
        "A-C01",
        {
            "identifierRegime": "repository-url",
            "url": url,
            "host": parsed.netloc,
            "path": repo_path,
            "citation": target_text,
        },
        make_evidence(source_resource_id, target_text or url, path),
        REFERENCED,
    )
    return node_id


def require_resource_id(resource: JsonDict) -> str:
    """Return the resource ID or raise a clear extraction error."""
    resource_id = resource.get("resource_id")
    if not resource_id:
        raise ValueError(f"Resource is missing resource_id: {resource!r}")
    return resource_id


def extract_resource(resource: JsonDict, builder: GraphBuilder) -> None:
    """Extract all deterministic nodes and edges from one HydroShare resource."""
    resource_type = resource.get("resource_type")
    if resource_type not in RESOURCE_TYPES:
        builder.skip(f"unknown_resource_type:{resource_type or 'missing'}")
    extract_dataset_resource(resource, builder)
    extract_agents(resource, builder)
    extract_metadata_nodes(resource, builder)
    extract_files(resource, builder)
    extract_tool_configuration(resource, builder)
    extract_relations(resource, builder)
    record_skipped_top_level_fields(resource, builder)


def record_skipped_top_level_fields(resource: JsonDict, builder: GraphBuilder) -> None:
    """Log non-empty top-level fields that have no deterministic mapping rule."""
    resource_type = resource.get("resource_type") or "unknown"
    for field_name, value in resource.items():
        if field_name in HANDLED_TOP_LEVEL_FIELDS:
            continue
        if value not in (None, "", [], {}):
            builder.skip(f"unmapped_top_level_field:{resource_type}:{field_name}")


def extract_corpus(resources: list[JsonDict]) -> tuple[JsonDict, Counter[str]]:
    """Extract deterministic KG records for the full HydroShare corpus."""
    resources_by_id = {require_resource_id(resource): resource for resource in resources}
    builder = GraphBuilder(resources_by_id)
    for resource in sorted(resources, key=require_resource_id):
        extract_resource(resource, builder)
    return builder.to_output(), builder.skipped


def write_output(output: JsonDict, path: Path) -> None:
    """Write the interim output JSON deterministically."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(output, handle, indent=2, ensure_ascii=False, sort_keys=True)
        handle.write("\n")


def log_summary(output: JsonDict, skipped: Counter[str]) -> None:
    """Log extraction counts and skipped-field diagnostics."""
    node_counts = Counter(node["class"] for node in output["nodes"])
    edge_counts = Counter(edge["relation"] for edge in output["edges"])
    logging.info("nodes: %s", len(output["nodes"]))
    logging.info("edges: %s", len(output["edges"]))
    logging.info("node classes: %s", dict(sorted(node_counts.items())))
    logging.info("edge relations: %s", dict(sorted(edge_counts.items())))
    if skipped:
        logging.info("skipped fields/predicates:")
        for reason, count in sorted(skipped.items()):
            logging.info("  %s: %s", reason, count)
    else:
        logging.info("skipped fields/predicates: none")


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments for the deterministic extractor."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input",
        type=Path,
        default=DEFAULT_INPUT,
        help="HydroShare corpus JSON path.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help="Interim KG nodes/edges JSON path.",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=("DEBUG", "INFO", "WARNING", "ERROR"),
        help="Logging verbosity.",
    )
    return parser.parse_args()


def main() -> None:
    """Run the deterministic HydroShare extraction pipeline."""
    args = parse_args()
    logging.basicConfig(level=args.log_level, format="%(levelname)s: %(message)s")
    resources = load_corpus(args.input)
    output, skipped = extract_corpus(resources)
    write_output(output, args.output)
    log_summary(output, skipped)
    logging.info("wrote %s", args.output)


if __name__ == "__main__":
    main()
