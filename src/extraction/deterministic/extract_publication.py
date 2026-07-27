"""Extract deterministic publication ontology mentions from the Phase A corpus.

The transformer is offline and reads only the consolidated Publication Phase A
JSON plus the machine-readable ontology specification. It emits the deterministic
bibliographic, citation, and availability backbone defined by the Publication
Phase B contract and mapping.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import os
import re
import sys
import unicodedata
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath
from typing import Any, Iterable, Mapping, Sequence
from urllib.parse import urlsplit, urlunsplit

import yaml


PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_INPUT = PROJECT_ROOT / "data/interim/papers/ciroh_publication_corpus.json"
DEFAULT_OUTPUT = PROJECT_ROOT / "data/interim/papers/publication_nodes_edges.json"
DEFAULT_ONTOLOGY_SPEC = PROJECT_ROOT / "src/ontology/ontology_spec.yaml"

OUTPUT_SCHEMA_VERSION = "1.0.0"
PHASE_B_VERSION = "1.0.2"
SUPPORTED_SOURCE_SCHEMAS = frozenset({"1.1.0"})
SUPPORTED_PHASE_A_VERSIONS = frozenset({"1.0.9"})
SOURCE_TYPE = "publication"
EXTRACTION_METHOD = "deterministic"
CURATED = "curated"
REFERENCED = "referenced"

NODE_REQUIRED_KEYS = frozenset(
    {
        "id",
        "class",
        "inventoryId",
        "attributes",
        "canonicalKey",
        "identityRegime",
        "curationStatus",
        "evidence",
        "internalLineage",
    }
)
EDGE_REQUIRED_KEYS = frozenset(
    {
        "id",
        "relation",
        "inventoryId",
        "source",
        "target",
        "attributes",
        "evidence",
        "internalLineage",
    }
)
EVIDENCE_REQUIRED_KEYS = frozenset(
    {"evidenceText", "sourceLocation", "extractionMethod", "sourceArtifact", "version"}
)

PUBLICATION_NODE_RULE_IDS = {
    "Paper": "A-P01",
    "Venue": "A-P02",
    "Person": "A-AG01",
    "Subject": "A-P04",
    "Identifier": "A-ID01",
    "DatasetMention": "A-P25",
    "DatasetResource": "A-D01",
    "Repository": "A-C01",
    "Tool": "A-DOM02",
}
PUBLICATION_RELATION_RULE_IDS = {
    ("hasAuthor", "Person"): "C-P01",
    ("publishedIn", "Venue"): "C-P02",
    ("hasSubject", "Subject"): "C-P03",
    ("hasIdentifier", "Paper"): "C-P04",
    ("cites", "Paper"): "C-P21",
    ("corrects", "Paper"): "C-P22",
    ("usesDataset", "DatasetResource"): "C-P20",
    ("usesDataset", "DatasetMention"): "C-P20",
    ("referencesDataset", "DatasetResource"): "C-P29",
    ("hasIdentifier", "DatasetResource"): "C-D04",
    ("hasIdentifier", "Repository"): "C-C06",
}

TOP_LEVEL_FIELDS = frozenset(
    {"schema_version", "phase_a_version", "source", "publications", "known_exclusions", "warnings", "summary"}
)
SOURCE_FIELDS = frozenset({"artifact_type", "corpus_cutoff", "raw_root", "selection_method"})
PUBLICATION_FIELDS = frozenset(
    {
        "local_paper_id",
        "canonical_artifact_id",
        "canonical_identifier",
        "identifiers",
        "record_type",
        "curation_status",
        "bibliographic",
        "content",
        "document_structure",
        "source_files",
        "bibliographic_relations",
        "reconciliation",
    }
)
BIBLIOGRAPHIC_FIELDS = frozenset(
    {"title", "authors", "year", "venue", "volume", "issue", "pages", "publisher", "language", "abstract", "abstract_source"}
)
AUTHOR_FIELDS = frozenset(
    {"display_name", "given_names", "family_name", "name_particles", "suffix", "literal_name", "raw_bibtex", "position"}
)
IDENTIFIER_FIELDS = frozenset({"scheme", "value", "uri"})
CONTENT_FIELDS = frozenset({"headings", "explicit_keywords", "reference_dois", "availability_identifiers"})
HEADING_FIELDS = frozenset({"level", "text", "normalized_text", "line_number"})
KEYWORD_FIELDS = frozenset({"raw_value", "value", "source_type", "source_location"})
REFERENCE_FIELDS = frozenset({"doi", "uri", "reference_text", "source_location", "occurrences"})
REFERENCE_OCCURRENCE_FIELDS = frozenset({"reference_text", "source_location"})
AVAILABILITY_FIELDS = frozenset(
    {"identifier_scheme", "identifier_value", "identifier_uri", "section_category", "section_title", "evidence_text", "source_location"}
)
SOURCE_LOCATION_FIELDS = frozenset({"source_artifact", "section", "line_start", "line_end"})
AVAILABILITY_LOCATION_FIELDS = frozenset({"source_artifact", "line_start", "line_end"})
DOCUMENT_STRUCTURE_FIELDS = frozenset({"page_count", "table_of_contents"})
TOC_FIELDS = frozenset({"title", "page_id", "heading_level", "polygon"})
SOURCE_FILE_FIELDS = frozenset(
    {"pdf_path", "markdown_path", "markdown_meta_path", "chunks_path", "chunks_meta_path", "marker_json_path", "marker_json_meta_path"}
)
RECONCILIATION_FIELDS = frozenset(
    {"excel_matched", "zotero_key_original", "bibtex_key", "bibtex_match_method", "bibtex_entry_type", "override_applied", "override_action", "conflicts", "warnings"}
)
CONFLICT_FIELDS = frozenset({"field", "excel_value", "bibtex_value", "resolution"})
RECONCILIATION_WARNING_FIELDS = frozenset({"category", "detail"})
BIBLIOGRAPHIC_RELATION_FIELDS = frozenset({"correction_of"})
KNOWN_EXCLUSION_FIELDS = frozenset(
    {"source_key", "source_type", "reason", "replacement_canonical_artifact_id"}
)

FIELD_DISPOSITIONS = {
    "schema_version": "validation/output",
    "phase_a_version": "validation/evidence/lineage/output",
    "source.*": "validation/stats/administrative-only",
    "publications[]": "node/edge mappings",
    "known_exclusions[]": "skipped",
    "warnings[]": "warning",
    "summary": "validation/stats",
    "local_paper_id": "internal lineage",
    "canonical_artifact_id": "identity/evidence",
    "canonical_identifier": "identity/validation",
    "identifiers[]": "Identifier/hasIdentifier",
    "record_type": "Paper attribute",
    "curation_status": "node curationStatus",
    "bibliographic.title": "Paper attribute/evidence",
    "bibliographic.authors[]": "Person/hasAuthor",
    "bibliographic.year": "Paper attribute",
    "bibliographic.venue": "Venue/publishedIn",
    "bibliographic.volume": "Paper attribute",
    "bibliographic.issue": "Paper attribute",
    "bibliographic.pages": "Paper attribute",
    "bibliographic.publisher": "Paper attribute",
    "bibliographic.language": "Paper attribute",
    "bibliographic.abstract": "Paper attribute",
    "bibliographic.abstract_source": "Paper attribute/lineage",
    "content.headings[]": "Paper attribute",
    "content.explicit_keywords[]": "Subject/hasSubject",
    "content.reference_dois[]": "citation target/edge/report",
    "content.availability_identifiers[]": "availability target/edge/report",
    "document_structure.page_count": "Paper attribute",
    "document_structure.table_of_contents[]": "Paper attribute; polygon administrative-only",
    "source_files.*": "internal lineage",
    "bibliographic_relations.correction_of": "corrects",
    "reconciliation.*": "validation/lineage/warning/stats",
}

DOI_RE = re.compile(r"^10\.\d{4,9}/[-._;()/:A-Z0-9]+$", re.IGNORECASE)
DOI_IN_TEXT_RE = re.compile(r"10\.\d{4,9}/[-._;()/:A-Z0-9]+", re.IGNORECASE)
HYDROSHARE_PATH_RE = re.compile(r"(?:^|/)resource/([0-9a-f]{32})(?:/|$)", re.IGNORECASE)
DATASET_TYPE_LABEL_RE = re.compile(
    r"(?:\[\s*data\s*set\s*\]|\[\s*dataset\s*\]|\(\s*data\s*set\s*\)|\(\s*dataset\s*\))",
    re.IGNORECASE,
)
REPOSITORY_TYPE_LABEL_RE = re.compile(
    r"(?:\[\s*(?:code\s+|source[- ]code\s+)?repository\s*\]|"
    r"\(\s*(?:code\s+|source[- ]code\s+)?repository\s*\)|"
    r"\brepository\s*:)",
    re.IGNORECASE,
)
SOFTWARE_TYPE_LABEL_RE = re.compile(
    r"(?:\[\s*software\s*\]|\(\s*software\s*\)|"
    r"\[\s*computer software\s*\]|\(\s*computer software\s*\))",
    re.IGNORECASE,
)
ANY_TYPE_LANGUAGE_RE = re.compile(
    r"(?:data\s+repository|software\s+version|journal\s+of\s+open\s+source\s+software|"
    r"dataset|data\s+set|software|repository|tool|model|code)",
    re.IGNORECASE,
)
SCHOLARLY_ARTICLE_STRUCTURE_RE = re.compile(
    r"\*?\d{1,4}\*?\s*\(\s*\d{1,4}\s*\)\s*,\s*"
    r"(?:[A-Za-z]?\d{1,8})(?:\s*[\-\u2013\u2014]\s*\d{1,8})?",
    re.IGNORECASE,
)
GITHUB_URL_IN_TEXT_RE = re.compile(r"https?://github\.com/[^\s<>()\[\]]+/[^\s<>()\[\]]+", re.IGNORECASE)
TYPE_LABEL_MAX_GAP = 160
AMBIGUOUS_REPOSITORY_DOI_PREFIXES = (
    "10.5281/zenodo.",
    "10.6084/m9.figshare.",
    "10.5061/dryad.",
    "10.7910/dvn/",
)
GITHUB_RESERVED_SEGMENTS = frozenset(
    {
        "about",
        "apps",
        "attachments",
        "badges",
        "collections",
        "events",
        "features",
        "gists",
        "login",
        "marketplace",
        "new",
        "organizations",
        "orgs",
        "pricing",
        "search",
        "settings",
        "site",
        "topics",
        "user-attachments",
        "users",
    }
)
FORBIDDEN_CONTROL_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")

JsonObject = dict[str, Any]


class InputValidationError(ValueError):
    """Raised when the Phase A corpus violates its declared contract."""

    def __init__(self, issues: Sequence[str]):
        super().__init__("Publication Phase A validation failed:\n- " + "\n- ".join(issues))
        self.issues = list(issues)


class OutputValidationError(ValueError):
    """Raised when the generated Phase B graph violates its contract."""

    def __init__(self, issues: Sequence[str]):
        super().__init__("Publication Phase B validation failed:\n- " + "\n- ".join(issues))
        self.issues = list(issues)


def stable_json(value: Any) -> str:
    """Serialize a JSON-compatible value canonically for comparisons."""
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def stable_hash(value: str) -> str:
    """Return the first 20 lowercase hexadecimal SHA-256 characters."""
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:20]


def sha256_bytes(value: bytes) -> str:
    """Return the complete lowercase SHA-256 digest for bytes."""
    return hashlib.sha256(value).hexdigest()


def sorted_unique(values: Iterable[Any]) -> list[Any]:
    """Return JSON-distinct values in deterministic canonical order."""
    distinct = {stable_json(value): value for value in values}
    return [distinct[key] for key in sorted(distinct)]


def normalize_text_key(value: str | None) -> str:
    """Apply NFKC, whitespace collapse, and case folding."""
    return " ".join(unicodedata.normalize("NFKC", str(value or "")).split()).casefold()


def normalize_doi(value: str | None) -> str | None:
    """Normalize and conservatively validate a DOI value."""
    if not value:
        return None
    normalized = str(value).strip().strip("<>`\"'")
    normalized = re.sub(r"^(?:https?://(?:dx\.)?doi\.org/|doi\s*:\s*)", "", normalized, flags=re.I)
    normalized = normalized.casefold()
    return normalized if DOI_RE.fullmatch(normalized) else None


def normalize_url(value: str | None) -> str | None:
    """Normalize an absolute HTTP(S) URL without decoding its path."""
    if not value:
        return None
    parsed = urlsplit(str(value).strip())
    if parsed.scheme.casefold() not in {"http", "https"} or not parsed.hostname:
        return None
    if any(token in str(value) for token in ("](", "<", ">")):
        return None
    host = parsed.hostname.casefold()
    port = f":{parsed.port}" if parsed.port else ""
    return urlunsplit((parsed.scheme.casefold(), host + port, parsed.path, parsed.query, parsed.fragment))


def normalize_github_repository_url(value: str | None) -> str | None:
    """Return an exact GitHub owner/repository root or ``None``."""
    normalized = normalize_url(value)
    if not normalized:
        return None
    parsed = urlsplit(normalized)
    if parsed.hostname != "github.com":
        return None
    segments = [segment for segment in parsed.path.split("/") if segment]
    if len(segments) < 2 or segments[0].casefold() in GITHUB_RESERVED_SEGMENTS:
        return None
    owner, repository = segments[:2]
    if repository.casefold().endswith(".git"):
        repository = repository[:-4]
    if not owner or not repository:
        return None
    return f"https://github.com/{owner}/{repository}"


def github_repository_identity_url(value: str | None) -> str | None:
    """Return the case-folded exact GitHub repository identity URL."""
    repository_url = normalize_github_repository_url(value)
    return repository_url.casefold() if repository_url else None


def extract_hydroshare_resource_id(value: str | None) -> str | None:
    """Extract an exact 32-character HydroShare resource identifier."""
    normalized = normalize_url(value)
    if not normalized:
        return None
    parsed = urlsplit(normalized)
    if not (parsed.hostname == "hydroshare.org" or parsed.hostname.endswith(".hydroshare.org")):
        return None
    match = HYDROSHARE_PATH_RE.search(parsed.path)
    return match.group(1).casefold() if match else None


def canonical_key(publication: Mapping[str, Any]) -> str:
    """Return the exact curated Paper identity key."""
    identifier = publication["canonical_identifier"]
    if identifier["scheme"] == "doi":
        doi = normalize_doi(identifier["value"])
        if not doi:
            raise ValueError("Invalid curated DOI")
        return f"doi:{doi}"
    url = normalize_url(identifier["value"])
    if not url:
        raise ValueError("Invalid curated canonical URL")
    return f"url:{url}"


def make_paper_id(key: str, referenced: bool = False) -> str:
    """Build a curated or referenced Paper ID from its exact key."""
    hash_input = key.replace(":", "|", 1) if referenced and key.startswith("doi:") else key
    return f"publication:paper:{stable_hash(hash_input)}"


def make_person_mention_id(paper_key: str, position: int) -> str:
    """Build one paper-scoped author mention ID."""
    return f"publication:person:{stable_hash(paper_key)}:{position:04d}"


def make_venue_id(normalized_name: str) -> str:
    """Build an exact-normalized Venue ID."""
    return f"publication:venue:{stable_hash(normalized_name)}"


def make_subject_id(normalized_label: str) -> str:
    """Build an exact-normalized Subject ID."""
    return f"publication:subject:{stable_hash(normalized_label)}"


def make_identifier_id(scheme: str, normalized_value: str) -> str:
    """Build an exact Identifier ID."""
    return f"publication:identifier:{stable_hash(f'{scheme}|{normalized_value}') }"


def make_dataset_resource_id(key: str) -> str:
    """Build a globally reusable DatasetResource ID."""
    return f"publication:dataset:{stable_hash(key)}"


def make_dataset_mention_id(paper_key: str, scheme: str, value: str) -> str:
    """Build a paper-scoped availability DatasetMention ID."""
    return f"publication:dataset-mention:{stable_hash(paper_key)}:{stable_hash(f'{scheme}|{value}') }"


def make_repository_id(key: str) -> str:
    """Build an exact referenced Repository ID."""
    return f"publication:repository:{stable_hash(key)}"


def make_tool_id(doi: str) -> str:
    """Build an exact software-DOI Tool ID."""
    return f"publication:tool:{stable_hash(f'doi|{doi}') }"


def make_edge_id(source: str, relation: str, target: str) -> str:
    """Build a deterministic semantic edge ID."""
    return f"publication:edge:{relation}:{stable_hash(f'{source}|{relation}|{target}') }"


def display_name(author: Mapping[str, Any]) -> str:
    """Return the authoritative Phase A author display value."""
    return str(author.get("display_name") or author.get("raw_bibtex") or "").strip()


def person_alignment_key(author: Mapping[str, Any]) -> str:
    """Build the weak name key used only for later author alignment."""
    if author.get("literal_name"):
        value = author["literal_name"]
    else:
        pieces = [
            *author.get("given_names", []),
            *author.get("name_particles", []),
            author.get("family_name"),
            author.get("suffix"),
        ]
        value = " ".join(str(piece) for piece in pieces if piece)
    return f"person-name:{normalize_text_key(value)}"


def serialize_deterministically(output: Mapping[str, Any]) -> bytes:
    """Serialize output as sorted UTF-8 JSON with one final newline."""
    return (json.dumps(output, indent=2, ensure_ascii=False, sort_keys=True) + "\n").encode("utf-8")


class OntologyRegistry:
    """Validate emitted mapping bindings and edge signatures against YAML."""

    def __init__(self, spec: Mapping[str, Any]):
        self.spec = spec
        self.classes_by_id = self._index(spec.get("classes", []), "class")
        self.relations_by_id = self._index(spec.get("relations", []), "relation")
        self.classes_by_name = {
            str(entry["name"]): entry for entry in self.classes_by_id.values()
        }
        self._validate_bindings()

    @staticmethod
    def _index(entries: Iterable[Mapping[str, Any]], kind: str) -> dict[str, Mapping[str, Any]]:
        """Index ontology entries by unique inventory ID."""
        indexed: dict[str, Mapping[str, Any]] = {}
        for entry in entries:
            inventory_id = str(entry.get("id") or "")
            if not inventory_id:
                raise ValueError(f"Ontology {kind} lacks inventory ID")
            if inventory_id in indexed:
                raise ValueError(f"Duplicate ontology inventory ID: {inventory_id}")
            if not entry.get("name"):
                raise ValueError(f"Ontology {kind} {inventory_id} lacks name")
            indexed[inventory_id] = entry
        return indexed

    def _validate_bindings(self) -> None:
        """Validate all Publication mapping bindings against ontology entries."""
        for class_name, inventory_id in PUBLICATION_NODE_RULE_IDS.items():
            entry = self.classes_by_id.get(inventory_id)
            if not entry or entry["name"] != class_name:
                raise ValueError(
                    f"Publication node binding {class_name}/{inventory_id} does not match ontology"
                )
        for (relation_name, _), inventory_id in PUBLICATION_RELATION_RULE_IDS.items():
            entry = self.relations_by_id.get(inventory_id)
            if not entry or entry["name"] != relation_name:
                raise ValueError(
                    f"Publication relation binding {relation_name}/{inventory_id} does not match ontology"
                )
        references_dataset = self.relations_by_id["C-P29"]
        if references_dataset.get("domain") != "Paper" or references_dataset.get("range") != "DatasetResource":
            raise ValueError("C-P29 must authorize Paper -> DatasetResource")

    def class_entry(self, class_name: str, inventory_id: str) -> Mapping[str, Any]:
        """Return and validate one emitted class/inventory pair."""
        entry = self.classes_by_id.get(inventory_id)
        if not entry or entry["name"] != class_name:
            raise ValueError(f"Unknown class/inventory pair: {class_name}/{inventory_id}")
        if entry.get("abstract") is True:
            raise ValueError(f"Cannot instantiate abstract class {class_name}")
        return entry

    def _class_iri(self, class_name: str) -> str | None:
        """Return the declared IRI used to recognize shared class aliases."""
        entry = self.classes_by_name.get(class_name)
        return str(entry.get("iri")) if entry else None

    def class_matches(self, emitted_class: str, expected: str) -> bool:
        """Return whether two class names denote the same YAML class identity."""
        if emitted_class == expected or expected == "owl:Thing":
            return True
        emitted_iri = self._class_iri(emitted_class)
        expected_iri = self._class_iri(expected)
        return bool(emitted_iri and emitted_iri == expected_iri)

    def validate_edge(
        self,
        relation: str,
        inventory_id: str,
        source_class: str,
        target_class: str,
    ) -> None:
        """Validate one emitted edge against its inventory-specific signature."""
        entry = self.relations_by_id.get(inventory_id)
        if not entry or entry["name"] != relation:
            raise ValueError(f"Unknown relation/inventory pair: {relation}/{inventory_id}")
        domains = entry.get("domain") if isinstance(entry.get("domain"), list) else [entry.get("domain")]
        ranges = entry.get("range") if isinstance(entry.get("range"), list) else [entry.get("range")]
        if not any(self.class_matches(source_class, str(item)) for item in domains):
            raise ValueError(
                f"Domain violation for {relation}/{inventory_id}: {source_class} not in {domains}"
            )
        if not any(self.class_matches(target_class, str(item)) for item in ranges):
            raise ValueError(
                f"Range violation for {relation}/{inventory_id}: {target_class} not in {ranges}"
            )


@dataclass
class Node:
    """One deterministic publication graph node."""

    id: str
    class_name: str
    inventory_id: str
    attributes: JsonObject
    canonical_key: str
    identity_regime: str
    curation_status: str
    evidence: JsonObject
    internal_lineage: JsonObject

    def as_dict(self) -> JsonObject:
        """Return the contract node representation."""
        return {
            "id": self.id,
            "class": self.class_name,
            "inventoryId": self.inventory_id,
            "attributes": self.attributes,
            "canonicalKey": self.canonical_key,
            "identityRegime": self.identity_regime,
            "curationStatus": self.curation_status,
            "evidence": self.evidence,
            "internalLineage": self.internal_lineage,
        }


@dataclass
class Edge:
    """One deterministic publication graph edge."""

    id: str
    relation: str
    inventory_id: str
    source: str
    target: str
    attributes: JsonObject
    evidence: JsonObject
    internal_lineage: JsonObject

    def as_dict(self) -> JsonObject:
        """Return the contract edge representation."""
        return {
            "id": self.id,
            "relation": self.relation,
            "inventoryId": self.inventory_id,
            "source": self.source,
            "target": self.target,
            "attributes": self.attributes,
            "evidence": self.evidence,
            "internalLineage": self.internal_lineage,
        }


@dataclass
class GraphBuilder:
    """Accumulate graph objects, reports, and source accounting safely."""

    phase_a_version: str
    ontology: OntologyRegistry
    nodes: dict[str, JsonObject] = field(default_factory=dict)
    edges: dict[str, JsonObject] = field(default_factory=dict)
    deferred: list[JsonObject] = field(default_factory=list)
    skipped: list[JsonObject] = field(default_factory=list)
    unresolved: list[JsonObject] = field(default_factory=list)
    warnings: list[JsonObject] = field(default_factory=list)
    citation_accounted: set[tuple[str, int]] = field(default_factory=set)
    availability_accounted: set[tuple[str, int]] = field(default_factory=set)

    def emit_node(self, node: Node) -> str:
        """Emit one node or reject a conflicting duplicate ID."""
        record = node.as_dict()
        self.ontology.class_entry(node.class_name, node.inventory_id)
        existing = self.nodes.get(node.id)
        if existing is not None and stable_json(existing) != stable_json(record):
            raise ValueError(f"Conflicting node ID: {node.id}")
        self.nodes[node.id] = record
        return node.id

    def upsert_exact_node(self, node: Node, declaration: Mapping[str, Any]) -> str:
        """Create or merge an exact node and all deterministic declarations."""
        record = node.as_dict()
        self.ontology.class_entry(node.class_name, node.inventory_id)
        existing = self.nodes.get(node.id)
        if existing is None:
            declarations = sort_declarations([dict(declaration)])
            record["attributes"]["sourceDeclarations"] = declarations
            apply_primary_declaration(record, declarations, self.phase_a_version)
            self.nodes[node.id] = record
            return node.id
        for key in ("id", "class", "inventoryId", "canonicalKey", "identityRegime"):
            if existing[key] != record[key]:
                raise ValueError(f"Conflicting exact node {node.id}: {key}")
        declarations = sort_declarations(
            [*existing["attributes"].get("sourceDeclarations", []), dict(declaration)]
        )
        existing["attributes"]["sourceDeclarations"] = declarations
        if existing["identityRegime"] == "github_repository_url":
            display_urls = sorted(
                {
                    str(value)
                    for value in (
                        existing["attributes"].get("htmlUrl"),
                        record["attributes"].get("htmlUrl"),
                    )
                    if value
                }
            )
            if display_urls:
                display_url = display_urls[0]
                owner, name = [
                    part for part in urlsplit(display_url).path.split("/") if part
                ][:2]
                existing["attributes"].update(
                    {"htmlUrl": display_url, "owner": owner, "name": name}
                )
        if record["curationStatus"] == CURATED:
            existing["curationStatus"] = CURATED
        apply_primary_declaration(existing, declarations, self.phase_a_version)
        return node.id

    def emit_edge(self, edge: Edge) -> str:
        """Emit one edge or merge its source declarations deterministically."""
        record = edge.as_dict()
        source = self.nodes.get(edge.source)
        target = self.nodes.get(edge.target)
        if source is None or target is None:
            raise ValueError(f"Dangling edge endpoint for {edge.id}")
        self.ontology.validate_edge(
            edge.relation,
            edge.inventory_id,
            str(source["class"]),
            str(target["class"]),
        )
        existing = self.edges.get(edge.id)
        if existing is None:
            self.edges[edge.id] = record
            return edge.id
        for key in ("id", "relation", "inventoryId", "source", "target"):
            if existing[key] != record[key]:
                raise ValueError(f"Conflicting edge ID {edge.id}: {key}")
        old_declarations = existing["attributes"].get("sourceDeclarations", [])
        new_declarations = record["attributes"].get("sourceDeclarations", [])
        if old_declarations or new_declarations:
            declarations = sort_declarations([*old_declarations, *new_declarations])
            existing["attributes"].update(
                {
                    key: value
                    for key, value in record["attributes"].items()
                    if key != "sourceDeclarations" and key not in existing["attributes"]
                }
            )
            existing["attributes"]["sourceDeclarations"] = declarations
            apply_primary_declaration(existing, declarations, self.phase_a_version)
        elif stable_json(existing) != stable_json(record):
            raise ValueError(f"Conflicting semantic edge: {edge.id}")
        return edge.id

    def record(
        self,
        bucket: str,
        publication_id: str,
        category: str,
        phase_a_field: str,
        reason: str,
        value: Any = None,
        source_line: int | None = None,
    ) -> None:
        """Append one deterministic report record to the selected bucket."""
        record = {
            "publicationId": publication_id,
            "category": category,
            "phaseAField": phase_a_field,
            "reason": reason,
            "value": value,
            "sourceLine": source_line,
        }
        getattr(self, bucket).append(record)


def build_evidence(
    evidence_text: str,
    source_artifact: str,
    phase_a_version: str,
) -> JsonObject:
    """Build the exact five-field public evidence object."""
    return {
        "evidenceText": str(evidence_text).strip(),
        "sourceLocation": source_artifact,
        "extractionMethod": EXTRACTION_METHOD,
        "sourceArtifact": source_artifact,
        "version": f"phase-a:{phase_a_version}",
    }


def build_internal_lineage(
    publication: Mapping[str, Any],
    phase_a_field: str,
    phase_a_version: str,
    *,
    section: str | None = None,
    line_start: int | None = None,
    line_end: int | None = None,
    author_position: int | None = None,
) -> JsonObject:
    """Build internal Phase A lineage without exposing it as public evidence."""
    lineage: JsonObject = {
        "phaseAField": phase_a_field,
        "localPaperId": str(publication["local_paper_id"]),
        "markdownPath": publication["source_files"]["markdown_path"],
        "phaseAVersion": phase_a_version,
    }
    optional = {
        "section": section,
        "lineStart": line_start,
        "lineEnd": line_end,
        "authorPosition": author_position,
    }
    lineage.update({key: value for key, value in optional.items() if value is not None})
    return lineage


def declaration_from_location(
    publication: Mapping[str, Any],
    phase_a_field: str,
    evidence_text: str,
    source_location: Mapping[str, Any] | None,
    *,
    curation_status: str = CURATED,
    extra: Mapping[str, Any] | None = None,
) -> JsonObject:
    """Build one sortable merged-entity or edge source declaration."""
    location = source_location or {}
    declaration: JsonObject = {
        "sourceArtifact": publication["canonical_artifact_id"],
        "evidenceText": str(evidence_text).strip(),
        "section": location.get("section"),
        "lineStart": location.get("line_start"),
        "lineEnd": location.get("line_end"),
        "phaseAField": phase_a_field,
        "_localPaperId": str(publication["local_paper_id"]),
        "_markdownPath": publication["source_files"]["markdown_path"],
        "_curationStatus": curation_status,
    }
    if extra:
        declaration.update(extra)
    return declaration


def declaration_sort_key(declaration: Mapping[str, Any]) -> tuple[Any, ...]:
    """Return the contract ordering for merged source declarations."""
    line_start = declaration.get("lineStart")
    line_end = declaration.get("lineEnd")
    return (
        0 if declaration.get("_curationStatus") == CURATED else 1,
        str(declaration.get("sourceArtifact") or ""),
        line_start is None,
        line_start if line_start is not None else 0,
        line_end is None,
        line_end if line_end is not None else 0,
        str(declaration.get("phaseAField") or ""),
        str(declaration.get("evidenceText") or ""),
        stable_json(declaration),
    )


def sort_declarations(declarations: Iterable[Mapping[str, Any]]) -> list[JsonObject]:
    """Deduplicate and sort source declarations by the contract ordering."""
    unique = {stable_json(item): dict(item) for item in declarations}
    return sorted(unique.values(), key=declaration_sort_key)


def apply_primary_declaration(
    record: JsonObject,
    declarations: Sequence[Mapping[str, Any]],
    phase_a_version: str,
) -> None:
    """Apply deterministic primary public evidence and internal lineage."""
    primary = declarations[0]
    record["evidence"] = build_evidence(
        str(primary["evidenceText"]), str(primary["sourceArtifact"]), phase_a_version
    )
    lineage = {
        "phaseAField": primary["phaseAField"],
        "localPaperId": primary["_localPaperId"],
        "markdownPath": primary["_markdownPath"],
        "phaseAVersion": phase_a_version,
    }
    for source_key, target_key in (
        ("section", "section"),
        ("lineStart", "lineStart"),
        ("lineEnd", "lineEnd"),
    ):
        if primary.get(source_key) is not None:
            lineage[target_key] = primary[source_key]
    record["internalLineage"] = lineage


def report_sort_key(record: Mapping[str, Any]) -> tuple[Any, ...]:
    """Return the deterministic report ordering required by the contract."""
    line = record.get("sourceLine")
    return (
        str(record.get("publicationId") or ""),
        str(record.get("category") or ""),
        str(record.get("phaseAField") or ""),
        line is None,
        line if line is not None else 0,
        str(record.get("reason") or ""),
        stable_json(record.get("value")),
    )


def _check_keys(value: Any, expected: frozenset[str], location: str, issues: list[str]) -> None:
    """Append an issue when one mapping has an unexpected schema shape."""
    if not isinstance(value, Mapping):
        issues.append(f"{location} must be an object")
        return
    actual = set(value)
    if actual != set(expected):
        issues.append(
            f"{location} keys differ: missing={sorted(set(expected) - actual)} "
            f"extra={sorted(actual - set(expected))}"
        )


def _walk_strings(value: Any, path: str = "$") -> Iterable[tuple[str, str]]:
    """Yield every string in a nested JSON-compatible value with its path."""
    if isinstance(value, str):
        yield path, value
    elif isinstance(value, Mapping):
        for key, child in value.items():
            yield from _walk_strings(child, f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from _walk_strings(child, f"{path}[{index}]")


def _valid_relative_path(value: Any) -> bool:
    """Return whether a source path is repository-relative and non-escaping."""
    if not isinstance(value, str) or not value or value.startswith(("/", "\\")):
        return False
    path = PurePosixPath(value)
    return ".." not in path.parts and not re.match(r"^[A-Za-z]:", value)


def _valid_location(value: Any, *, require_section: bool = True) -> bool:
    """Return whether a Phase A source-location record has a valid line range."""
    expected = SOURCE_LOCATION_FIELDS if require_section else AVAILABILITY_LOCATION_FIELDS
    if not isinstance(value, Mapping) or set(value) != set(expected):
        return False
    start, end = value.get("line_start"), value.get("line_end")
    return (
        isinstance(start, int)
        and isinstance(end, int)
        and start >= 1
        and end >= start
        and isinstance(value.get("source_artifact"), str)
        and bool(value.get("source_artifact"))
    )


def validate_input(corpus: Mapping[str, Any], validate_frozen_snapshot: bool = False) -> list[str]:
    """Validate the complete Phase A input contract before extraction."""
    issues: list[str] = []
    _check_keys(corpus, TOP_LEVEL_FIELDS, "$", issues)
    if corpus.get("schema_version") not in SUPPORTED_SOURCE_SCHEMAS:
        issues.append(f"Unsupported source schema: {corpus.get('schema_version')!r}")
    if corpus.get("phase_a_version") not in SUPPORTED_PHASE_A_VERSIONS:
        issues.append(f"Unsupported Phase A version: {corpus.get('phase_a_version')!r}")
    source = corpus.get("source")
    _check_keys(source, SOURCE_FIELDS, "source", issues)
    if isinstance(source, Mapping) and source.get("artifact_type") != SOURCE_TYPE:
        issues.append("source.artifact_type must be publication")
    publications = corpus.get("publications")
    if not isinstance(publications, list):
        return [*issues, "publications must be an array"]

    local_ids: set[str] = set()
    artifact_ids: set[str] = set()
    for pub_index, publication in enumerate(publications):
        base = f"publications[{pub_index}]"
        _check_keys(publication, PUBLICATION_FIELDS, base, issues)
        if not isinstance(publication, Mapping):
            continue
        local_id = str(publication.get("local_paper_id") or "")
        artifact_id = str(publication.get("canonical_artifact_id") or "")
        if not local_id or local_id in local_ids:
            issues.append(f"{base}.local_paper_id is empty or duplicated: {local_id!r}")
        if not artifact_id or artifact_id in artifact_ids:
            issues.append(f"{base}.canonical_artifact_id is empty or duplicated: {artifact_id!r}")
        local_ids.add(local_id)
        artifact_ids.add(artifact_id)
        if publication.get("curation_status") != CURATED:
            issues.append(f"{base}.curation_status must be curated")

        identifier = publication.get("canonical_identifier")
        _check_keys(identifier, IDENTIFIER_FIELDS, f"{base}.canonical_identifier", issues)
        if isinstance(identifier, Mapping):
            scheme = identifier.get("scheme")
            normalized = normalize_doi(identifier.get("value")) if scheme == "doi" else normalize_url(identifier.get("value"))
            if normalized is None:
                issues.append(f"{base}.canonical_identifier is malformed")
            expected_uri = f"https://doi.org/{normalized}" if scheme == "doi" and normalized else normalized
            if expected_uri and identifier.get("uri") != expected_uri:
                issues.append(f"{base}.canonical_identifier URI is inconsistent")
            if expected_uri and artifact_id != expected_uri:
                issues.append(f"{base}.canonical_artifact_id is inconsistent")

        identifiers = publication.get("identifiers")
        if not isinstance(identifiers, list) or not identifiers:
            issues.append(f"{base}.identifiers must be a nonempty array")
        else:
            seen_identifiers: set[tuple[str, str]] = set()
            for index, item in enumerate(identifiers):
                _check_keys(item, IDENTIFIER_FIELDS, f"{base}.identifiers[{index}]", issues)
                scheme = item.get("scheme") if isinstance(item, Mapping) else None
                normalized = normalize_doi(item.get("value")) if scheme == "doi" else normalize_url(item.get("value")) if isinstance(item, Mapping) else None
                if not normalized:
                    issues.append(f"{base}.identifiers[{index}] is malformed")
                    continue
                key = (str(scheme), normalized)
                if key in seen_identifiers:
                    issues.append(f"{base}.identifiers contains duplicate {key}")
                seen_identifiers.add(key)
                expected_uri = f"https://doi.org/{normalized}" if scheme == "doi" else normalized
                if item.get("uri") != expected_uri:
                    issues.append(f"{base}.identifiers[{index}] URI is inconsistent")

        bibliographic = publication.get("bibliographic")
        _check_keys(bibliographic, BIBLIOGRAPHIC_FIELDS, f"{base}.bibliographic", issues)
        if isinstance(bibliographic, Mapping):
            for field_name in ("title", "year", "venue"):
                if bibliographic.get(field_name) in (None, ""):
                    issues.append(f"{base}.bibliographic.{field_name} is required")
            authors = bibliographic.get("authors")
            if not isinstance(authors, list) or not authors:
                issues.append(f"{base}.bibliographic.authors must be nonempty")
            else:
                positions: list[int] = []
                for index, author in enumerate(authors):
                    _check_keys(author, AUTHOR_FIELDS, f"{base}.bibliographic.authors[{index}]", issues)
                    if isinstance(author, Mapping):
                        positions.append(author.get("position"))
                        if not display_name(author):
                            issues.append(f"{base}.bibliographic.authors[{index}] lacks display name")
                if positions != list(range(1, len(authors) + 1)):
                    issues.append(f"{base}.author positions are not contiguous")

        content = publication.get("content")
        _check_keys(content, CONTENT_FIELDS, f"{base}.content", issues)
        if isinstance(content, Mapping):
            for index, heading in enumerate(content.get("headings", [])):
                _check_keys(heading, HEADING_FIELDS, f"{base}.content.headings[{index}]", issues)
            for index, keyword in enumerate(content.get("explicit_keywords", [])):
                _check_keys(keyword, KEYWORD_FIELDS, f"{base}.content.explicit_keywords[{index}]", issues)
                if isinstance(keyword, Mapping) and not _valid_location(keyword.get("source_location")):
                    issues.append(f"{base}.content.explicit_keywords[{index}] has invalid source location")
            seen_dois: set[str] = set()
            for index, reference in enumerate(content.get("reference_dois", [])):
                _check_keys(reference, REFERENCE_FIELDS, f"{base}.content.reference_dois[{index}]", issues)
                if not isinstance(reference, Mapping):
                    continue
                doi = normalize_doi(reference.get("doi"))
                if not doi or reference.get("uri") != f"https://doi.org/{doi}":
                    issues.append(f"{base}.content.reference_dois[{index}] has invalid DOI/URI")
                elif doi in seen_dois:
                    issues.append(f"{base}.content.reference_dois contains duplicate {doi}")
                seen_dois.add(doi or "")
                if not _valid_location(reference.get("source_location")):
                    issues.append(f"{base}.content.reference_dois[{index}] has invalid source location")
                occurrences = reference.get("occurrences")
                if not isinstance(occurrences, list) or not occurrences:
                    issues.append(f"{base}.content.reference_dois[{index}].occurrences is empty")
                else:
                    for occurrence_index, occurrence in enumerate(occurrences):
                        _check_keys(
                            occurrence,
                            REFERENCE_OCCURRENCE_FIELDS,
                            f"{base}.content.reference_dois[{index}].occurrences[{occurrence_index}]",
                            issues,
                        )
                        if isinstance(occurrence, Mapping) and not _valid_location(occurrence.get("source_location")):
                            issues.append(f"{base}.reference occurrence has invalid location")
            seen_availability: set[tuple[str, str]] = set()
            for index, availability in enumerate(content.get("availability_identifiers", [])):
                _check_keys(availability, AVAILABILITY_FIELDS, f"{base}.content.availability_identifiers[{index}]", issues)
                if not isinstance(availability, Mapping):
                    continue
                scheme = availability.get("identifier_scheme")
                normalized = normalize_doi(availability.get("identifier_value")) if scheme == "doi" else normalize_url(availability.get("identifier_value"))
                if not normalized:
                    issues.append(f"{base}.availability[{index}] is malformed")
                else:
                    key = (str(scheme), normalized)
                    if key in seen_availability:
                        issues.append(f"{base}.availability contains duplicate {key}")
                    seen_availability.add(key)
                    expected_uri = f"https://doi.org/{normalized}" if scheme == "doi" else normalized
                    if availability.get("identifier_uri") != expected_uri:
                        issues.append(f"{base}.availability[{index}] URI is inconsistent")
                if not _valid_location(
                    availability.get("source_location"), require_section=False
                ):
                    issues.append(f"{base}.availability[{index}] has invalid source location")

        structure = publication.get("document_structure")
        _check_keys(structure, DOCUMENT_STRUCTURE_FIELDS, f"{base}.document_structure", issues)
        if isinstance(structure, Mapping):
            for index, toc in enumerate(structure.get("table_of_contents", [])):
                _check_keys(toc, TOC_FIELDS, f"{base}.document_structure.table_of_contents[{index}]", issues)
        files = publication.get("source_files")
        _check_keys(files, SOURCE_FILE_FIELDS, f"{base}.source_files", issues)
        if isinstance(files, Mapping):
            for field_name, path in files.items():
                if not _valid_relative_path(path):
                    issues.append(f"{base}.source_files.{field_name} is not repository-relative")
        relations = publication.get("bibliographic_relations")
        _check_keys(relations, BIBLIOGRAPHIC_RELATION_FIELDS, f"{base}.bibliographic_relations", issues)
        correction = relations.get("correction_of") if isinstance(relations, Mapping) else None
        if correction is not None:
            _check_keys(correction, IDENTIFIER_FIELDS, f"{base}.correction_of", issues)
            doi = normalize_doi(correction.get("value")) if isinstance(correction, Mapping) else None
            if not doi or correction.get("scheme") != "doi" or correction.get("uri") != f"https://doi.org/{doi}":
                issues.append(f"{base}.correction_of is malformed")
        reconciliation = publication.get("reconciliation")
        _check_keys(reconciliation, RECONCILIATION_FIELDS, f"{base}.reconciliation", issues)
        if isinstance(reconciliation, Mapping):
            for index, conflict in enumerate(reconciliation.get("conflicts", [])):
                _check_keys(conflict, CONFLICT_FIELDS, f"{base}.reconciliation.conflicts[{index}]", issues)
            for index, warning in enumerate(reconciliation.get("warnings", [])):
                _check_keys(warning, RECONCILIATION_WARNING_FIELDS, f"{base}.reconciliation.warnings[{index}]", issues)

    for index, exclusion in enumerate(corpus.get("known_exclusions", [])):
        _check_keys(exclusion, KNOWN_EXCLUSION_FIELDS, f"known_exclusions[{index}]", issues)
    for path, text in _walk_strings(corpus):
        if FORBIDDEN_CONTROL_RE.search(text):
            issues.append(f"Forbidden control character at {path}")
            break

    summary = corpus.get("summary")
    if not isinstance(summary, Mapping):
        issues.append("summary must be an object")
    else:
        expected_summary = {
            "publication_count": len(publications),
            "known_exclusion_count": len(corpus.get("known_exclusions", [])),
            "warning_count": sum(len(pub["reconciliation"]["warnings"]) for pub in publications) + len(corpus.get("warnings", [])),
            "conflict_count": sum(len(pub["reconciliation"]["conflicts"]) for pub in publications),
            "explicit_keyword_count": sum(len(pub["content"]["explicit_keywords"]) for pub in publications),
            "reference_doi_count": sum(len(pub["content"]["reference_dois"]) for pub in publications),
            "availability_identifier_count": sum(len(pub["content"]["availability_identifiers"]) for pub in publications),
        }
        for key, expected in expected_summary.items():
            if summary.get(key) != expected:
                issues.append(f"summary.{key}={summary.get(key)!r}, expected {expected!r}")
    if validate_frozen_snapshot:
        issues.extend(validate_frozen_input(corpus))
    return issues


def validate_frozen_input(corpus: Mapping[str, Any]) -> list[str]:
    """Validate the published Phase A frozen source anchors."""
    publications = corpus["publications"]
    references = [item for pub in publications for item in pub["content"]["reference_dois"]]
    availability = [item for pub in publications for item in pub["content"]["availability_identifiers"]]
    curated_dois = {
        normalize_doi(pub["canonical_identifier"]["value"])
        for pub in publications
        if pub["canonical_identifier"]["scheme"] == "doi"
    }
    self_references = sum(
        normalize_doi(reference["doi"])
        == (normalize_doi(pub["canonical_identifier"]["value"]) if pub["canonical_identifier"]["scheme"] == "doi" else None)
        for pub in publications
        for reference in pub["content"]["reference_dois"]
    )
    values = {
        "publications": len(publications),
        "curated_dois": len(curated_dois),
        "url_only": sum(pub["canonical_identifier"]["scheme"] == "url" for pub in publications),
        "identifiers": sum(len(pub["identifiers"]) for pub in publications),
        "authors": sum(len(pub["bibliographic"]["authors"]) for pub in publications),
        "venues": len({normalize_text_key(pub["bibliographic"]["venue"]) for pub in publications}),
        "keywords": sum(len(pub["content"]["explicit_keywords"]) for pub in publications),
        "subjects": len({normalize_text_key(item["value"]) for pub in publications for item in pub["content"]["explicit_keywords"]}),
        "references": len(references),
        "unique_references": len({normalize_doi(item["doi"]) for item in references}),
        "curated_overlap": len({normalize_doi(item["doi"]) for item in references} & curated_dois),
        "self_references": self_references,
        "availability": len(availability),
        "corrections": sum(pub["bibliographic_relations"]["correction_of"] is not None for pub in publications),
    }
    expected = {
        "publications": 228,
        "curated_dois": 227,
        "url_only": 1,
        "identifiers": 455,
        "authors": 1602,
        "venues": 84,
        "keywords": 373,
        "subjects": 317,
        "references": 8856,
        "unique_references": 6720,
        "curated_overlap": 112,
        "self_references": 23,
        "availability": 299,
        "corrections": 1,
    }
    return [f"Frozen input {key}={values[key]}, expected {value}" for key, value in expected.items() if values[key] != value]


def _normalize_doi_text_match(value: str) -> str | None:
    """Normalize a DOI-like text match after removing only unmatched wrappers."""
    candidate = value.rstrip(".,;:")
    while candidate.endswith(")") and candidate.count(")") > candidate.count("("):
        candidate = candidate[:-1]
    return normalize_doi(candidate)


def _doi_spans(reference_text: str, target_doi: str) -> list[tuple[int, int, str]]:
    """Return deterministic DOI declaration spans, including exact target literals."""
    text = str(reference_text)
    spans: set[tuple[int, int, str]] = set()
    for match in DOI_IN_TEXT_RE.finditer(text):
        normalized = _normalize_doi_text_match(match.group(0))
        if normalized:
            end = match.start() + len(match.group(0).rstrip(".,;:"))
            while end > match.start() and text[end - 1] == ")" and text[match.start():end].count(")") > text[match.start():end].count("("):
                end -= 1
            spans.add((match.start(), end, normalized))
    for match in re.finditer(re.escape(target_doi), text, re.IGNORECASE):
        spans.add((match.start(), match.end(), target_doi))
    return sorted(spans, key=lambda item: (item[0], item[1], item[2]))


def extract_doi_local_context(reference_text: str, doi: str) -> str:
    """Return the target's occurrence-local segment without crossing another DOI."""
    text = str(reference_text)
    normalized_doi = normalize_doi(doi)
    if normalized_doi is None:
        return ""
    spans = _doi_spans(text, normalized_doi)
    target_spans = [span for span in spans if span[2] == normalized_doi]
    if not target_spans:
        return ""
    first_start = min(span[0] for span in target_spans)
    last_end = max(span[1] for span in target_spans)
    other_spans = [span for span in spans if span[2] != normalized_doi]
    if any(first_start < start < last_end for start, _, _ in other_spans):
        return ""
    previous = [span for span in other_spans if span[1] <= first_start]
    following = [span for span in other_spans if span[0] >= last_end]
    left_boundary = max((span[1] for span in previous), default=0)
    right_boundary = min((span[0] for span in following), default=len(text))

    line_start = text.rfind("\n", left_boundary, first_start)
    if line_start >= 0:
        left_boundary = line_start + 1
    line_end = text.find("\n", last_end, right_boundary)
    if line_end >= 0:
        right_boundary = line_end
    return text[left_boundary:right_boundary]


def _marker_is_structurally_associated(
    context: str, marker: re.Match[str], target_start: int
) -> bool:
    """Return whether a type label occupies the target DOI's local type slot."""
    gap = context[marker.end():target_start]
    return len(gap) <= TYPE_LABEL_MAX_GAP and not DOI_IN_TEXT_RE.search(gap)


def classify_context_signals(context: str, doi: str | None = None) -> set[str]:
    """Return only strong structural type signals attributable to one target DOI."""
    if not context:
        return set()
    target_start = len(context)
    if doi is not None:
        normalized_doi = normalize_doi(doi)
        if normalized_doi is None:
            return set()
        target_spans = [
            span for span in _doi_spans(context, normalized_doi) if span[2] == normalized_doi
        ]
        if not target_spans:
            return set()
        target_start = min(span[0] for span in target_spans)
    prefix = context[:target_start]
    if SCHOLARLY_ARTICLE_STRUCTURE_RE.search(prefix):
        return set()

    signals: set[str] = set()
    marker_rules = (
        (DATASET_TYPE_LABEL_RE, "DatasetResource"),
        (REPOSITORY_TYPE_LABEL_RE, "Repository"),
        (SOFTWARE_TYPE_LABEL_RE, "Tool"),
    )
    for pattern, target_class in marker_rules:
        matches = list(pattern.finditer(prefix))
        if matches and _marker_is_structurally_associated(context, matches[-1], target_start):
            signals.add(target_class)
    for match in GITHUB_URL_IN_TEXT_RE.finditer(prefix):
        if (
            normalize_github_repository_url(match.group(0))
            and _marker_is_structurally_associated(context, match, target_start)
        ):
            signals.add("Repository")
    return signals


def classify_cited_doi_occurrence(
    doi: str,
    declaration: Mapping[str, Any],
    curated_dois: set[str],
) -> tuple[str, str, str]:
    """Classify one Phase A cited-DOI occurrence without borrowing other evidence."""
    if doi in curated_dois:
        return "curated_paper", "curated_doi_match", doi
    if doi.startswith("10.4211/hs."):
        return "strong_dataset", "exact_hydroshare_doi", doi
    evidence_text = str(declaration["evidenceText"])
    context = extract_doi_local_context(evidence_text, doi)
    signals = classify_context_signals(context, doi)
    if len(signals) > 1:
        return "conflicting", "conflicting_structural_type_labels", context
    if signals:
        target_class = next(iter(signals))
        decision = {
            "DatasetResource": "strong_dataset",
            "Repository": "strong_repository",
            "Tool": "strong_tool",
        }[target_class]
        return decision, f"structural_{decision.removeprefix('strong_')}_label", context
    if doi.startswith(AMBIGUOUS_REPOSITORY_DOI_PREFIXES):
        return "ambiguous", "ambiguous_repository_namespace", context
    if SCHOLARLY_ARTICLE_STRUCTURE_RE.search(context):
        return "untyped_scholarly_reference", "scholarly_article_structure", context
    if ANY_TYPE_LANGUAGE_RE.search(evidence_text):
        return "untyped_scholarly_reference", "weak_or_unattributed_type_language", context
    return "untyped_scholarly_reference", "no_strong_non_paper_evidence", context


def classify_cited_doi_target(
    doi: str,
    declarations: Sequence[Mapping[str, Any]],
    curated_dois: set[str],
) -> tuple[str | None, str]:
    """Choose one deterministic global cited-DOI target class or disposition."""
    if doi in curated_dois:
        return "Paper", "curated_doi_match"
    if doi.startswith("10.4211/hs."):
        return "DatasetResource", "exact_hydroshare_doi"
    occurrence_decisions: list[str] = []
    for declaration in declarations:
        decision = declaration.get("occurrenceDecision")
        if decision is None:
            decision, _, _ = classify_cited_doi_occurrence(
                doi, declaration, curated_dois
            )
        occurrence_decisions.append(str(decision))
    strong_classes = {
        {
            "strong_dataset": "DatasetResource",
            "strong_repository": "Repository",
            "strong_tool": "Tool",
        }[decision]
        for decision in occurrence_decisions
        if decision in {"strong_dataset", "strong_repository", "strong_tool"}
    }
    if "conflicting" in occurrence_decisions or len(strong_classes) > 1:
        return None, "conflicting_cited_doi_type"
    if strong_classes:
        return next(iter(strong_classes)), "consistent_strong_occurrence_type_evidence"
    if "ambiguous" in occurrence_decisions:
        return None, "ambiguous_cited_doi_type"
    return "Paper", "default_bibliographic_paper"


@dataclass(frozen=True)
class PublicationContext:
    """Precomputed identity and source information for one curated publication."""

    publication: Mapping[str, Any]
    canonical_key: str
    paper_id: str
    paper_hash: str


def _placeholder_evidence(publication: Mapping[str, Any], phase_a_version: str) -> JsonObject:
    """Build valid evidence used until an exact node selects its primary source."""
    return build_evidence(
        str(publication["bibliographic"]["title"]),
        str(publication["canonical_artifact_id"]),
        phase_a_version,
    )


def _placeholder_lineage(
    publication: Mapping[str, Any], phase_a_field: str, phase_a_version: str
) -> JsonObject:
    """Build valid lineage used until an exact node selects its primary source."""
    return build_internal_lineage(publication, phase_a_field, phase_a_version)


def emit_semantic_edge(
    builder: GraphBuilder,
    source: str,
    relation: str,
    inventory_id: str,
    target: str,
    attributes: Mapping[str, Any],
    publication: Mapping[str, Any],
    phase_a_field: str,
    evidence_text: str,
    *,
    source_location: Mapping[str, Any] | None = None,
    declarations: Sequence[Mapping[str, Any]] | None = None,
) -> str:
    """Build and emit one fully evidenced semantic edge."""
    location = source_location or {}
    edge_attributes = dict(attributes)
    if declarations is not None:
        sorted_declarations = sort_declarations(declarations)
        edge_attributes["sourceDeclarations"] = sorted_declarations
        primary = sorted_declarations[0]
        evidence = build_evidence(
            str(primary["evidenceText"]),
            str(primary["sourceArtifact"]),
            builder.phase_a_version,
        )
        lineage = {
            "phaseAField": primary["phaseAField"],
            "localPaperId": primary["_localPaperId"],
            "markdownPath": primary["_markdownPath"],
            "phaseAVersion": builder.phase_a_version,
        }
        for key in ("section", "lineStart", "lineEnd"):
            if primary.get(key) is not None:
                lineage[key] = primary[key]
    else:
        evidence = build_evidence(
            evidence_text,
            str(publication["canonical_artifact_id"]),
            builder.phase_a_version,
        )
        lineage = build_internal_lineage(
            publication,
            phase_a_field,
            builder.phase_a_version,
            section=location.get("section"),
            line_start=location.get("line_start"),
            line_end=location.get("line_end"),
        )
    return builder.emit_edge(
        Edge(
            id=make_edge_id(source, relation, target),
            relation=relation,
            inventory_id=inventory_id,
            source=source,
            target=target,
            attributes=edge_attributes,
            evidence=evidence,
            internal_lineage=lineage,
        )
    )


def ensure_identifier(
    builder: GraphBuilder,
    publication: Mapping[str, Any],
    scheme: str,
    value: str,
    uri: str,
    phase_a_field: str,
    *,
    curation_status: str,
    evidence_text: str | None = None,
    source_location: Mapping[str, Any] | None = None,
) -> str:
    """Create or merge an exact Identifier node."""
    normalized = normalize_doi(value) if scheme == "doi" else normalize_url(value)
    if not normalized:
        raise ValueError(f"Invalid identifier {scheme}:{value}")
    declaration = declaration_from_location(
        publication,
        phase_a_field,
        evidence_text or value,
        source_location,
        curation_status=curation_status,
        extra={"declaredValue": value, "declaredUri": uri},
    )
    node_id = make_identifier_id(scheme, normalized)
    node = Node(
        id=node_id,
        class_name="Identifier",
        inventory_id="A-ID01",
        attributes={
            "scheme": scheme,
            "value": value,
            "normalizedValue": normalized,
            "uri": uri,
        },
        canonical_key=f"{scheme}:{normalized}",
        identity_regime="exact_identifier",
        curation_status=curation_status,
        evidence=_placeholder_evidence(publication, builder.phase_a_version),
        internal_lineage=_placeholder_lineage(publication, phase_a_field, builder.phase_a_version),
    )
    return builder.upsert_exact_node(node, declaration)


def ensure_venue(
    builder: GraphBuilder,
    publication: Mapping[str, Any],
) -> str:
    """Create or merge an exact-normalized Venue node."""
    venue = str(publication["bibliographic"]["venue"])
    key = normalize_text_key(venue)
    declaration = declaration_from_location(
        publication, "bibliographic.venue", venue, None, curation_status=CURATED
    )
    node = Node(
        id=make_venue_id(key),
        class_name="Venue",
        inventory_id="A-P02",
        attributes={"name": venue, "normalizedName": key},
        canonical_key=f"venue-name:{key}",
        identity_regime="normalized_exact_name",
        curation_status=CURATED,
        evidence=_placeholder_evidence(publication, builder.phase_a_version),
        internal_lineage=_placeholder_lineage(publication, "bibliographic.venue", builder.phase_a_version),
    )
    return builder.upsert_exact_node(node, declaration)


def ensure_subject(
    builder: GraphBuilder,
    publication: Mapping[str, Any],
    keyword: Mapping[str, Any],
    index: int,
) -> str:
    """Create or merge one exact-normalized explicit Subject node."""
    key = normalize_text_key(keyword["value"])
    field_name = f"content.explicit_keywords[{index}]"
    declaration = declaration_from_location(
        publication,
        field_name,
        str(keyword["raw_value"]),
        keyword["source_location"],
        curation_status=CURATED,
    )
    node = Node(
        id=make_subject_id(key),
        class_name="Subject",
        inventory_id="A-P04",
        attributes={"label": keyword["raw_value"], "normalizedLabel": key},
        canonical_key=f"subject:{key}",
        identity_regime="normalized_exact_label",
        curation_status=CURATED,
        evidence=_placeholder_evidence(publication, builder.phase_a_version),
        internal_lineage=_placeholder_lineage(publication, field_name, builder.phase_a_version),
    )
    return builder.upsert_exact_node(node, declaration)


def ensure_external_target(
    builder: GraphBuilder,
    target_class: str,
    exact_key: str,
    declarations: Sequence[Mapping[str, Any]],
    publication: Mapping[str, Any],
    attributes: Mapping[str, Any],
) -> str:
    """Create or merge one globally exact external target node."""
    if target_class == "Paper":
        node_id = make_paper_id(exact_key, referenced=True)
        identity_regime = "doi"
        inventory_id = "A-P01"
    elif target_class == "DatasetResource":
        node_id = make_dataset_resource_id(exact_key.replace(":", "|", 1))
        identity_regime = "hydroshare_resource_id" if exact_key.startswith("hydroshare:") else "dataset_doi"
        inventory_id = "A-D01"
    elif target_class == "Repository":
        if exact_key.startswith("url:"):
            repository_url = exact_key.removeprefix("url:")
            node_id = make_repository_id(f"github-repo-url|{repository_url}")
            identity_regime = "github_repository_url"
        else:
            node_id = make_repository_id(exact_key.replace(":", "|", 1))
            identity_regime = "repository_doi"
        inventory_id = "A-C01"
    elif target_class == "Tool":
        doi = exact_key.removeprefix("doi:")
        node_id = make_tool_id(doi)
        identity_regime = "software_doi"
        inventory_id = "A-DOM02"
    else:
        raise ValueError(f"Unsupported external target class {target_class}")
    primary = sort_declarations(declarations)[0]
    node = Node(
        id=node_id,
        class_name=target_class,
        inventory_id=inventory_id,
        attributes=dict(attributes),
        canonical_key=exact_key,
        identity_regime=identity_regime,
        curation_status=REFERENCED,
        evidence=build_evidence(
            str(primary["evidenceText"]),
            str(primary["sourceArtifact"]),
            builder.phase_a_version,
        ),
        internal_lineage={
            "phaseAField": primary["phaseAField"],
            "localPaperId": primary["_localPaperId"],
            "markdownPath": primary["_markdownPath"],
            "phaseAVersion": builder.phase_a_version,
        },
    )
    for declaration in declarations:
        builder.upsert_exact_node(node, declaration)
    return node_id


def emit_curated_backbone(
    corpus: Mapping[str, Any],
    builder: GraphBuilder,
) -> tuple[list[PublicationContext], dict[str, PublicationContext]]:
    """Emit curated Papers and deterministic bibliographic backbone nodes/edges."""
    contexts: list[PublicationContext] = []
    doi_index: dict[str, PublicationContext] = {}
    for publication in sorted(corpus["publications"], key=canonical_key):
        key = canonical_key(publication)
        paper_id = make_paper_id(key)
        context = PublicationContext(publication, key, paper_id, stable_hash(key))
        contexts.append(context)
        if key.startswith("doi:"):
            doi_index[key.removeprefix("doi:")] = context
        bibliography = publication["bibliographic"]
        abstract_source = bibliography["abstract_source"]
        paper_attributes = {
            "title": bibliography["title"],
            "recordType": publication["record_type"],
            "year": bibliography["year"],
            "volume": bibliography["volume"],
            "issue": bibliography["issue"],
            "pages": bibliography["pages"],
            "publisher": bibliography["publisher"],
            "language": bibliography["language"],
            "abstract": bibliography["abstract"],
            "abstractSourceType": abstract_source.get("source_type") if abstract_source else None,
            "canonicalArtifactId": publication["canonical_artifact_id"],
            "pageCount": publication["document_structure"]["page_count"],
            "headingCount": len(publication["content"]["headings"]),
            "headings": [
                {
                    "level": item["level"],
                    "text": item["text"],
                    "normalizedText": item["normalized_text"],
                    "lineNumber": item["line_number"],
                }
                for item in publication["content"]["headings"]
            ],
            "tableOfContentsEntryCount": len(publication["document_structure"]["table_of_contents"]),
            "tableOfContents": [
                {
                    "title": item["title"],
                    "pageId": item["page_id"],
                    "headingLevel": item["heading_level"],
                }
                for item in publication["document_structure"]["table_of_contents"]
            ],
        }
        lineage = build_internal_lineage(
            publication,
            f"publications[canonical_artifact_id={publication['canonical_artifact_id']}]",
            builder.phase_a_version,
        )
        lineage.update(
            {
                "pdfPath": publication["source_files"]["pdf_path"],
                "bibtexMatchMethod": publication["reconciliation"]["bibtex_match_method"],
                "overrideApplied": publication["reconciliation"]["override_applied"],
                "overrideAction": publication["reconciliation"]["override_action"],
            }
        )
        builder.emit_node(
            Node(
                id=paper_id,
                class_name="Paper",
                inventory_id="A-P01",
                attributes=paper_attributes,
                canonical_key=key,
                identity_regime="doi" if key.startswith("doi:") else "canonical_url",
                curation_status=CURATED,
                evidence=build_evidence(
                    str(bibliography["title"]),
                    str(publication["canonical_artifact_id"]),
                    builder.phase_a_version,
                ),
                internal_lineage=lineage,
            )
        )

        for identifier_index, identifier in enumerate(publication["identifiers"]):
            identifier_id = ensure_identifier(
                builder,
                publication,
                identifier["scheme"],
                identifier["value"],
                identifier["uri"],
                f"identifiers[{identifier_index}]",
                curation_status=CURATED,
            )
            emit_semantic_edge(
                builder,
                paper_id,
                "hasIdentifier",
                "C-P04",
                identifier_id,
                {
                    "identifierOrder": identifier_index + 1,
                    "isCanonical": identifier["uri"] == publication["canonical_artifact_id"],
                },
                publication,
                f"identifiers[{identifier_index}]",
                str(identifier["value"]),
            )

        for author in bibliography["authors"]:
            position = int(author["position"])
            person_id = make_person_mention_id(key, position)
            name = display_name(author)
            builder.emit_node(
                Node(
                    id=person_id,
                    class_name="Person",
                    inventory_id="A-AG01",
                    attributes={
                        "displayName": name,
                        "givenNames": author["given_names"],
                        "familyName": author["family_name"],
                        "nameParticles": author["name_particles"],
                        "suffix": author["suffix"],
                        "literalName": author["literal_name"],
                        "rawBibtex": author["raw_bibtex"],
                        "authorPosition": position,
                        "sourcePaperCanonicalKey": key,
                    },
                    canonical_key=person_alignment_key(author),
                    identity_regime="paper_author_mention",
                    curation_status=CURATED,
                    evidence=build_evidence(
                        name,
                        str(publication["canonical_artifact_id"]),
                        builder.phase_a_version,
                    ),
                    internal_lineage=build_internal_lineage(
                        publication,
                        f"bibliographic.authors[position={position}]",
                        builder.phase_a_version,
                        author_position=position,
                    ),
                )
            )
            emit_semantic_edge(
                builder,
                paper_id,
                "hasAuthor",
                "C-P01",
                person_id,
                {"authorPosition": position},
                publication,
                f"bibliographic.authors[position={position}]",
                name,
            )

        venue_id = ensure_venue(builder, publication)
        emit_semantic_edge(
            builder,
            paper_id,
            "publishedIn",
            "C-P02",
            venue_id,
            {},
            publication,
            "bibliographic.venue",
            str(bibliography["venue"]),
        )
        for keyword_index, keyword in enumerate(publication["content"]["explicit_keywords"]):
            subject_id = ensure_subject(builder, publication, keyword, keyword_index)
            emit_semantic_edge(
                builder,
                paper_id,
                "hasSubject",
                "C-P03",
                subject_id,
                {"keywordOrder": keyword_index + 1, "sourceType": keyword["source_type"]},
                publication,
                f"content.explicit_keywords[{keyword_index}]",
                str(keyword["raw_value"]),
                source_location=keyword["source_location"],
            )
    return contexts, doi_index


def reference_declarations(
    publication: Mapping[str, Any], reference: Mapping[str, Any], reference_index: int
) -> list[JsonObject]:
    """Return every authoritative occurrence declaration for one DOI record."""
    declarations: list[JsonObject] = []
    for occurrence_index, occurrence in enumerate(reference["occurrences"]):
        declarations.append(
            declaration_from_location(
                publication,
                (
                    f"content.reference_dois[{reference_index}]"
                    f".occurrences[{occurrence_index}]"
                ),
                str(occurrence["reference_text"]),
                occurrence["source_location"],
                curation_status=CURATED,
                extra={"doi": reference["doi"]},
            )
        )
    return declarations


def availability_declaration(
    publication: Mapping[str, Any], availability: Mapping[str, Any], index: int
) -> JsonObject:
    """Return the authoritative declaration for one availability identifier."""
    return declaration_from_location(
        publication,
        f"content.availability_identifiers[{index}]",
        str(availability["evidence_text"]),
        availability["source_location"],
        curation_status=CURATED,
        extra={
            "sectionCategory": availability["section_category"],
            "sectionTitle": availability["section_title"],
            "identifierScheme": availability["identifier_scheme"],
            "identifierValue": availability["identifier_value"],
        },
    )


@dataclass(frozen=True)
class CitationTargetDecision:
    """One global, order-independent cited DOI classification."""

    doi: str
    target_class: str | None
    reason: str
    declarations: tuple[JsonObject, ...]


def build_global_citation_target_registry(
    contexts: Sequence[PublicationContext], curated_dois: set[str]
) -> dict[str, CitationTargetDecision]:
    """Classify occurrences independently, then aggregate each DOI exactly once."""
    declarations_by_doi: dict[str, list[JsonObject]] = defaultdict(list)
    for context in contexts:
        publication = context.publication
        for reference_index, reference in enumerate(
            publication["content"]["reference_dois"]
        ):
            doi = normalize_doi(reference["doi"])
            if doi is None:
                raise ValueError("Phase A citation DOI became invalid after validation")
            declarations_by_doi[doi].extend(
                reference_declarations(publication, reference, reference_index)
            )
    registry: dict[str, CitationTargetDecision] = {}
    for doi in sorted(declarations_by_doi):
        enriched_declarations: list[JsonObject] = []
        for declaration in sort_declarations(declarations_by_doi[doi]):
            occurrence_decision, evidence_category, evidence_text = (
                classify_cited_doi_occurrence(doi, declaration, curated_dois)
            )
            enriched = dict(declaration)
            enriched.update(
                {
                    "occurrenceDecision": occurrence_decision,
                    "typeEvidenceCategory": evidence_category,
                    "typeEvidenceText": evidence_text,
                }
            )
            enriched_declarations.append(enriched)
        declarations = tuple(sort_declarations(enriched_declarations))
        target_class, reason = classify_cited_doi_target(
            doi, declarations, curated_dois
        )
        registry[doi] = CitationTargetDecision(
            doi=doi,
            target_class=target_class,
            reason=reason,
            declarations=declarations,
        )
    return registry


def citation_declarations_for_reference(
    decision: CitationTargetDecision,
    publication: Mapping[str, Any],
    reference_index: int,
) -> list[JsonObject]:
    """Return the enriched occurrence decisions for one Phase A DOI record."""
    field_prefix = f"content.reference_dois[{reference_index}].occurrences["
    declarations = [
        dict(declaration)
        for declaration in decision.declarations
        if declaration.get("sourceArtifact") == publication["canonical_artifact_id"]
        and str(declaration.get("phaseAField", "")).startswith(field_prefix)
    ]
    if not declarations:
        raise ValueError(
            "Global citation registry lost the source occurrence declarations for "
            f"{decision.doi} in {publication['canonical_artifact_id']}"
        )
    return sort_declarations(declarations)


def citation_decision_audit_value(decision: CitationTargetDecision) -> JsonObject:
    """Return the complete public occurrence audit for a target with no node."""
    return {
        "doi": decision.doi,
        "globalDecision": decision.reason,
        "occurrenceDecisions": [
            {
                key: value
                for key, value in declaration.items()
                if not key.startswith("_")
            }
            for declaration in decision.declarations
        ],
    }


def cited_target_attributes(target_class: str, doi: str) -> JsonObject:
    """Return intrinsic attributes for a DOI-identified cited target."""
    if target_class == "Paper":
        return {
            "title": None,
            "recordType": None,
            "year": None,
            "doi": doi,
            "canonicalArtifactId": f"https://doi.org/{doi}",
            "referenceStub": True,
        }
    if target_class == "DatasetResource":
        return {
            "title": None,
            "resourceId": None,
            "doi": doi,
            "url": None,
            "referenceStub": True,
        }
    if target_class == "Repository":
        return {
            "htmlUrl": None,
            "owner": None,
            "name": None,
            "doi": doi,
            "referenceStub": True,
        }
    if target_class == "Tool":
        return {
            "name": None,
            "doi": doi,
            "canonicalArtifactId": f"https://doi.org/{doi}",
            "referenceStub": True,
        }
    raise ValueError(f"Unsupported cited target class {target_class}")


def ensure_doi_target(
    builder: GraphBuilder,
    decision: CitationTargetDecision,
    doi_index: Mapping[str, PublicationContext],
    source_publication: Mapping[str, Any],
) -> str:
    """Create or reuse the one globally classified target for a DOI."""
    if decision.target_class is None:
        raise ValueError("Cannot create unresolved cited DOI target")
    if decision.target_class == "Paper" and decision.doi in doi_index:
        return doi_index[decision.doi].paper_id
    target_key = f"doi:{decision.doi}"
    return ensure_external_target(
        builder,
        decision.target_class,
        target_key,
        decision.declarations,
        source_publication,
        cited_target_attributes(decision.target_class, decision.doi),
    )


def emit_external_doi_identifier(
    builder: GraphBuilder,
    target_id: str,
    target_class: str,
    decision: CitationTargetDecision,
    publication: Mapping[str, Any],
) -> None:
    """Attach a DOI Identifier when the target class authorizes that edge."""
    if target_class not in {"DatasetResource", "Repository"}:
        return
    primary = decision.declarations[0]
    location = {
        "section": primary.get("section"),
        "line_start": primary.get("lineStart"),
        "line_end": primary.get("lineEnd"),
    }
    identifier_id = ensure_identifier(
        builder,
        publication,
        "doi",
        decision.doi,
        f"https://doi.org/{decision.doi}",
        str(primary["phaseAField"]),
        curation_status=REFERENCED,
        evidence_text=str(primary["evidenceText"]),
        source_location=location,
    )
    relation_id = "C-D04" if target_class == "DatasetResource" else "C-C06"
    emit_semantic_edge(
        builder,
        target_id,
        "hasIdentifier",
        relation_id,
        identifier_id,
        {"sourceDeclarations": list(decision.declarations)},
        publication,
        str(primary["phaseAField"]),
        str(primary["evidenceText"]),
        declarations=decision.declarations,
    )


def process_citations(
    contexts: Sequence[PublicationContext],
    doi_index: Mapping[str, PublicationContext],
    registry: Mapping[str, CitationTargetDecision],
    builder: GraphBuilder,
) -> None:
    """Emit globally typed citation targets, edges, and exact dispositions."""
    emitted_target_identifiers: set[tuple[str, str]] = set()
    for context in contexts:
        publication = context.publication
        source_doi = context.canonical_key.removeprefix("doi:") if context.canonical_key.startswith("doi:") else None
        for reference_index, reference in enumerate(
            publication["content"]["reference_dois"]
        ):
            account_key = (str(publication["local_paper_id"]), reference_index)
            doi = normalize_doi(reference["doi"])
            if doi is None:
                raise ValueError("Invalid citation DOI after input validation")
            field_name = f"content.reference_dois[{reference_index}]"
            source_line = reference["source_location"]["line_start"]
            if doi == source_doi:
                builder.record(
                    "skipped",
                    str(publication["canonical_artifact_id"]),
                    "self_reference_doi_matches_source",
                    field_name,
                    "reference DOI equals the source Paper DOI",
                    doi,
                    source_line,
                )
                builder.citation_accounted.add(account_key)
                continue
            decision = registry[doi]
            if decision.target_class is None:
                bucket = (
                    "unresolved"
                    if decision.reason == "conflicting_cited_doi_type"
                    else "deferred"
                )
                builder.record(
                    bucket,
                    str(publication["canonical_artifact_id"]),
                    decision.reason,
                    field_name,
                    "global cited DOI type could not be resolved deterministically",
                    citation_decision_audit_value(decision),
                    source_line,
                )
                builder.citation_accounted.add(account_key)
                continue

            target_id = ensure_doi_target(
                builder, decision, doi_index, publication
            )
            identifier_key = (target_id, decision.target_class)
            if identifier_key not in emitted_target_identifiers:
                emit_external_doi_identifier(
                    builder, target_id, decision.target_class, decision, publication
                )
                emitted_target_identifiers.add(identifier_key)
            declarations = citation_declarations_for_reference(
                decision, publication, reference_index
            )
            if decision.target_class == "Paper":
                emit_semantic_edge(
                    builder,
                    context.paper_id,
                    "cites",
                    "C-P21",
                    target_id,
                    {
                        "doi": doi,
                        "targetIsCurated": doi in doi_index,
                    },
                    publication,
                    field_name,
                    str(reference["reference_text"]),
                    declarations=declarations,
                )
            elif decision.target_class == "DatasetResource":
                emit_semantic_edge(
                    builder,
                    context.paper_id,
                    "referencesDataset",
                    "C-P29",
                    target_id,
                    {"doi": doi, "typingEvidence": decision.reason},
                    publication,
                    field_name,
                    str(reference["reference_text"]),
                    declarations=declarations,
                )
            else:
                reason = (
                    "paper_repository_relation_not_declared"
                    if decision.target_class == "Repository"
                    else "paper_tool_relation_requires_semantic_context"
                )
                builder.record(
                    "deferred",
                    str(publication["canonical_artifact_id"]),
                    reason,
                    field_name,
                    "typed citation target has no authorized deterministic Paper relation",
                    doi,
                    source_line,
                )
            builder.citation_accounted.add(account_key)


def _availability_normalized_value(availability: Mapping[str, Any]) -> str:
    """Return the already-validated normalized availability identity value."""
    if availability["identifier_scheme"] == "doi":
        value = normalize_doi(availability["identifier_value"])
    else:
        value = normalize_url(availability["identifier_value"])
    if value is None:
        raise ValueError("Invalid availability identifier after input validation")
    return value


def ensure_hydroshare_target(
    builder: GraphBuilder,
    publication: Mapping[str, Any],
    availability: Mapping[str, Any],
    index: int,
) -> tuple[str, str]:
    """Create an exact HydroShare DatasetResource and Identifier."""
    scheme = str(availability["identifier_scheme"])
    normalized = _availability_normalized_value(availability)
    resource_id = extract_hydroshare_resource_id(normalized) if scheme == "url" else None
    exact_key = f"hydroshare:{resource_id}" if resource_id else f"doi:{normalized}"
    declaration = availability_declaration(publication, availability, index)
    target_id = ensure_external_target(
        builder,
        "DatasetResource",
        exact_key,
        [declaration],
        publication,
        {
            "title": None,
            "resourceId": resource_id,
            "doi": normalized if scheme == "doi" else None,
            "url": normalized if scheme == "url" else None,
            "referenceStub": True,
        },
    )
    identifier_id = ensure_identifier(
        builder,
        publication,
        scheme,
        normalized,
        f"https://doi.org/{normalized}" if scheme == "doi" else normalized,
        f"content.availability_identifiers[{index}]",
        curation_status=REFERENCED,
        evidence_text=str(availability["evidence_text"]),
        source_location=availability["source_location"],
    )
    emit_semantic_edge(
        builder,
        target_id,
        "hasIdentifier",
        "C-D04",
        identifier_id,
        {},
        publication,
        f"content.availability_identifiers[{index}]",
        str(availability["evidence_text"]),
        declarations=[declaration],
    )
    return target_id, identifier_id


def ensure_github_target(
    builder: GraphBuilder,
    publication: Mapping[str, Any],
    availability: Mapping[str, Any],
    index: int,
    repository_url: str,
) -> str:
    """Create an exact GitHub Repository and URL Identifier."""
    parsed = urlsplit(repository_url)
    owner, name = [part for part in parsed.path.split("/") if part][:2]
    identity_url = github_repository_identity_url(repository_url)
    if identity_url is None:
        raise ValueError("Invalid GitHub repository URL after exact normalization")
    exact_key = f"url:{identity_url}"
    declaration = availability_declaration(publication, availability, index)
    target_id = ensure_external_target(
        builder,
        "Repository",
        exact_key,
        [declaration],
        publication,
        {
            "htmlUrl": repository_url,
            "owner": owner,
            "name": name,
            "doi": None,
            "referenceStub": True,
        },
    )
    identifier_id = ensure_identifier(
        builder,
        publication,
        "url",
        identity_url,
        identity_url,
        f"content.availability_identifiers[{index}]",
        curation_status=REFERENCED,
        evidence_text=str(availability["evidence_text"]),
        source_location=availability["source_location"],
    )
    emit_semantic_edge(
        builder,
        target_id,
        "hasIdentifier",
        "C-C06",
        identifier_id,
        {},
        publication,
        f"content.availability_identifiers[{index}]",
        str(availability["evidence_text"]),
        declarations=[declaration],
    )
    return target_id


def ensure_dataset_mention(
    builder: GraphBuilder,
    context: PublicationContext,
    availability: Mapping[str, Any],
    index: int,
) -> str:
    """Create one paper-scoped generic data-availability mention."""
    publication = context.publication
    scheme = str(availability["identifier_scheme"])
    normalized = _availability_normalized_value(availability)
    mention_id = make_dataset_mention_id(context.canonical_key, scheme, normalized)
    field_name = f"content.availability_identifiers[{index}]"
    builder.emit_node(
        Node(
            id=mention_id,
            class_name="DatasetMention",
            inventory_id="A-P25",
            attributes={
                "identifierScheme": scheme,
                "identifierValue": availability["identifier_value"],
                "identifierUri": availability["identifier_uri"],
                "sectionCategory": availability["section_category"],
                "sectionTitle": availability["section_title"],
                "sourcePaperCanonicalKey": context.canonical_key,
            },
            canonical_key=f"{scheme}:{normalized}",
            identity_regime="paper_availability_mention",
            curation_status=CURATED,
            evidence=build_evidence(
                str(availability["evidence_text"]),
                str(publication["canonical_artifact_id"]),
                builder.phase_a_version,
            ),
            internal_lineage=build_internal_lineage(
                publication,
                field_name,
                builder.phase_a_version,
                section=availability["section_title"],
                line_start=availability["source_location"]["line_start"],
                line_end=availability["source_location"]["line_end"],
            ),
        )
    )
    emit_semantic_edge(
        builder,
        context.paper_id,
        "usesDataset",
        "C-P20",
        mention_id,
        {
            "sectionCategory": availability["section_category"],
            "sectionTitle": availability["section_title"],
            "identifierScheme": scheme,
            "identifierValue": availability["identifier_value"],
        },
        publication,
        field_name,
        str(availability["evidence_text"]),
        source_location=availability["source_location"],
    )
    return mention_id


def _strong_doi_class_from_availability(
    doi: str, availability: Mapping[str, Any]
) -> str | None:
    """Return one structural availability DOI class without consulting citations."""
    context = extract_doi_local_context(str(availability["evidence_text"]), doi)
    signals = classify_context_signals(context, doi)
    return next(iter(signals)) if len(signals) == 1 else None


def _availability_decision(
    doi: str,
    target_class: str,
    publication: Mapping[str, Any],
    availability: Mapping[str, Any],
    index: int,
    citation_registry: Mapping[str, CitationTargetDecision],
) -> CitationTargetDecision:
    """Reuse a matching strong citation decision or build an availability decision."""
    global_decision = citation_registry.get(doi)
    if global_decision and global_decision.target_class == target_class:
        return global_decision
    return CitationTargetDecision(
        doi,
        target_class,
        "strong_availability_type_evidence",
        (availability_declaration(publication, availability, index),),
    )


def emit_availability_dataset_resource(
    builder: GraphBuilder,
    context: PublicationContext,
    availability: Mapping[str, Any],
    index: int,
    decision: CitationTargetDecision,
) -> None:
    """Reuse one DOI DatasetResource and emit its source-scoped usesDataset fact."""
    publication = context.publication
    field_name = f"content.availability_identifiers[{index}]"
    availability_source = availability_declaration(publication, availability, index)
    merged_decision = CitationTargetDecision(
        doi=decision.doi,
        target_class=decision.target_class,
        reason=decision.reason,
        declarations=tuple(
            sort_declarations([*decision.declarations, availability_source])
        ),
    )
    target_id = ensure_doi_target(builder, merged_decision, {}, publication)
    emit_external_doi_identifier(
        builder, target_id, "DatasetResource", merged_decision, publication
    )
    emit_semantic_edge(
        builder,
        context.paper_id,
        "usesDataset",
        "C-P20",
        target_id,
        {
            "sectionCategory": availability["section_category"],
            "sectionTitle": availability["section_title"],
            "identifierScheme": availability["identifier_scheme"],
            "identifierValue": availability["identifier_value"],
        },
        publication,
        field_name,
        str(availability["evidence_text"]),
        declarations=[availability_source],
    )


def process_availability(
    contexts: Sequence[PublicationContext],
    citation_registry: Mapping[str, CitationTargetDecision],
    builder: GraphBuilder,
) -> None:
    """Apply the complete conservative availability decision table."""
    for context in contexts:
        publication = context.publication
        for index, availability in enumerate(
            publication["content"]["availability_identifiers"]
        ):
            account_key = (str(publication["local_paper_id"]), index)
            field_name = f"content.availability_identifiers[{index}]"
            scheme = str(availability["identifier_scheme"])
            normalized = _availability_normalized_value(availability)
            category = str(availability["section_category"])
            source_line = availability["source_location"]["line_start"]
            is_hydroshare = (
                scheme == "doi" and normalized.startswith("10.4211/hs.")
            ) or (scheme == "url" and extract_hydroshare_resource_id(normalized) is not None)
            repository_url = (
                normalize_github_repository_url(normalized) if scheme == "url" else None
            )

            if is_hydroshare:
                target_id, _ = ensure_hydroshare_target(
                    builder, publication, availability, index
                )
                declaration = availability_declaration(publication, availability, index)
                emit_semantic_edge(
                    builder,
                    context.paper_id,
                    "usesDataset",
                    "C-P20",
                    target_id,
                    {
                        "sectionCategory": category,
                        "sectionTitle": availability["section_title"],
                        "identifierScheme": scheme,
                        "identifierValue": availability["identifier_value"],
                    },
                    publication,
                    field_name,
                    str(availability["evidence_text"]),
                    declarations=[declaration],
                )
            elif repository_url:
                ensure_github_target(
                    builder, publication, availability, index, repository_url
                )
                builder.record(
                    "deferred",
                    str(publication["canonical_artifact_id"]),
                    "paper_repository_relation_not_declared",
                    field_name,
                    "exact GitHub Repository has no authorized deterministic Paper relation",
                    repository_url,
                    source_line,
                )
            elif scheme == "url" and urlsplit(normalized).hostname and (
                urlsplit(normalized).hostname == "hydroshare.org"
                or str(urlsplit(normalized).hostname).endswith(".hydroshare.org")
            ):
                builder.record(
                    "unresolved",
                    str(publication["canonical_artifact_id"]),
                    "hydroshare_url_missing_resource_id",
                    field_name,
                    "HydroShare URL lacks an exact resource identifier",
                    normalized,
                    source_line,
                )
            else:
                global_decision = (
                    citation_registry.get(normalized) if scheme == "doi" else None
                )
                local_typed_class = (
                    _strong_doi_class_from_availability(normalized, availability)
                    if scheme == "doi"
                    else None
                )

                if category == "data_availability":
                    if (
                        scheme == "doi"
                        and global_decision is not None
                        and global_decision.target_class == "DatasetResource"
                    ):
                        emit_availability_dataset_resource(
                            builder,
                            context,
                            availability,
                            index,
                            global_decision,
                        )
                    else:
                        ensure_dataset_mention(builder, context, availability, index)
                else:
                    mixed_category = category in {
                        "data_and_code_availability",
                        "code_and_data_availability",
                    }
                    typed_class = (
                        global_decision.target_class
                        if global_decision
                        and global_decision.target_class
                        in {"DatasetResource", "Repository", "Tool"}
                        else local_typed_class
                        if global_decision is None
                        or global_decision.target_class is None
                        else None
                    )
                    if mixed_category and typed_class == "DatasetResource":
                        decision = _availability_decision(
                            normalized,
                            typed_class,
                            publication,
                            availability,
                            index,
                            citation_registry,
                        )
                        emit_availability_dataset_resource(
                            builder, context, availability, index, decision
                        )
                    elif typed_class in {"Repository", "Tool"}:
                        decision = _availability_decision(
                            normalized,
                            typed_class,
                            publication,
                            availability,
                            index,
                            citation_registry,
                        )
                        target_id = ensure_doi_target(
                            builder, decision, {}, publication
                        )
                        emit_external_doi_identifier(
                            builder, target_id, typed_class, decision, publication
                        )
                        reason = (
                            "paper_repository_relation_not_declared"
                            if typed_class == "Repository"
                            else "paper_tool_relation_requires_semantic_context"
                        )
                        builder.record(
                            "deferred",
                            str(publication["canonical_artifact_id"]),
                            reason,
                            field_name,
                            "typed availability target has no authorized deterministic Paper relation",
                            normalized,
                            source_line,
                        )
                    else:
                        builder.record(
                            "deferred",
                            str(publication["canonical_artifact_id"]),
                            (
                                "availability_mixed_target_type"
                                if mixed_category
                                else "availability_target_type_unresolved"
                            ),
                            field_name,
                            "availability identifier does not establish an authorized target relation",
                            normalized,
                            source_line,
                        )
            builder.availability_accounted.add(account_key)


def process_corrections(
    contexts: Sequence[PublicationContext],
    doi_index: Mapping[str, PublicationContext],
    builder: GraphBuilder,
) -> None:
    """Resolve deterministic corrigendum relations against curated Papers."""
    for context in contexts:
        correction = context.publication["bibliographic_relations"]["correction_of"]
        if correction is None:
            continue
        doi = normalize_doi(correction["value"])
        target = doi_index.get(doi or "")
        if target is None:
            raise OutputValidationError(
                [
                    "correction_target_not_found: "
                    f"{context.publication['canonical_artifact_id']} -> {doi}"
                ]
            )
        emit_semantic_edge(
            builder,
            context.paper_id,
            "corrects",
            "C-P22",
            target.paper_id,
            {"relationSource": "curation_override"},
            context.publication,
            "bibliographic_relations.correction_of",
            str(correction["value"]),
        )


def propagate_phase_a_reports(corpus: Mapping[str, Any], builder: GraphBuilder) -> None:
    """Preserve exclusions, warnings, and reconciliation conflicts for audit."""
    for index, exclusion in enumerate(corpus["known_exclusions"]):
        builder.record(
            "skipped",
            str(exclusion["replacement_canonical_artifact_id"]),
            "known_phase_a_exclusion",
            f"known_exclusions[{index}]",
            str(exclusion["reason"]),
            exclusion,
        )
    for index, warning in enumerate(corpus["warnings"]):
        builder.record(
            "warnings",
            "publication-corpus",
            str(warning.get("category", "phase_a_warning")),
            f"warnings[{index}]",
            "propagated Phase A top-level warning",
            warning.get("detail"),
        )
    for context in contexts_from_corpus(corpus):
        publication = context.publication
        artifact = str(publication["canonical_artifact_id"])
        for index, warning in enumerate(publication["reconciliation"]["warnings"]):
            detail = warning.get("detail")
            line = detail.get("line_number") if isinstance(detail, Mapping) else None
            builder.record(
                "warnings",
                artifact,
                str(warning["category"]),
                f"reconciliation.warnings[{index}]",
                "propagated Phase A reconciliation warning",
                detail,
                line if isinstance(line, int) else None,
            )
        for index, conflict in enumerate(publication["reconciliation"]["conflicts"]):
            builder.record(
                "warnings",
                artifact,
                "excel_bibtex_conflict",
                f"reconciliation.conflicts[{index}]",
                str(conflict["resolution"]),
                conflict,
            )


def contexts_from_corpus(corpus: Mapping[str, Any]) -> list[PublicationContext]:
    """Build sorted publication contexts without emitting graph objects."""
    return [
        PublicationContext(publication, canonical_key(publication), make_paper_id(canonical_key(publication)), stable_hash(canonical_key(publication)))
        for publication in sorted(corpus["publications"], key=canonical_key)
    ]


def _counter_dict(values: Iterable[str]) -> dict[str, int]:
    """Return a key-sorted count dictionary."""
    return dict(sorted(Counter(values).items()))


def finalize_source_declarations(records: Iterable[JsonObject]) -> None:
    """Remove internal merge bookkeeping from public source declarations."""
    for record in records:
        declarations = record.get("attributes", {}).get("sourceDeclarations")
        if not declarations:
            continue
        public_declarations = [
            {key: value for key, value in declaration.items() if not key.startswith("_")}
            for declaration in declarations
        ]
        record["attributes"]["sourceDeclarations"] = public_declarations


def build_stats(
    corpus: Mapping[str, Any],
    builder: GraphBuilder,
    source_corpus_sha256: str,
) -> JsonObject:
    """Compute all contract statistics from emitted objects and reports."""
    nodes = list(builder.nodes.values())
    edges = list(builder.edges.values())
    reports = [*builder.deferred, *builder.skipped, *builder.unresolved]
    citation_deferred_categories = {
        "ambiguous_cited_doi_type",
        "conflicting_cited_doi_type",
        "paper_repository_relation_not_declared",
        "paper_tool_relation_requires_semantic_context",
    }
    availability_deferred_categories = {
        "availability_mixed_target_type",
        "availability_target_type_unresolved",
        "hydroshare_url_missing_resource_id",
    }
    referenced_targets = [
        node
        for node in nodes
        if node["curationStatus"] == REFERENCED
        and node["class"] in {"Paper", "DatasetResource", "Repository", "Tool"}
    ]
    citation_edges = [
        edge for edge in edges if edge["relation"] in {"cites", "referencesDataset"}
    ]
    uses_edges = [edge for edge in edges if edge["relation"] == "usesDataset"]
    nodes_by_id = {node["id"]: node for node in nodes}
    citation_target_ids_by_class: dict[str, set[str]] = defaultdict(set)
    for edge in citation_edges:
        citation_target_ids_by_class[str(nodes_by_id[edge["target"]]["class"])].add(
            str(edge["target"])
        )
    for node in referenced_targets:
        declarations = node["attributes"].get("sourceDeclarations", [])
        if node["class"] in {"Repository", "Tool"} and any(
            str(declaration.get("phaseAField", "")).startswith(
                "content.reference_dois["
            )
            for declaration in declarations
        ):
            citation_target_ids_by_class[str(node["class"])].add(str(node["id"]))
    return {
        "sourceCorpusSha256": source_corpus_sha256,
        "sourcePublicationCount": len(corpus["publications"]),
        "sourceAuthorOccurrenceCount": sum(
            len(pub["bibliographic"]["authors"]) for pub in corpus["publications"]
        ),
        "sourceKeywordOccurrenceCount": sum(
            len(pub["content"]["explicit_keywords"]) for pub in corpus["publications"]
        ),
        "sourceReferenceDoiCount": sum(
            len(pub["content"]["reference_dois"]) for pub in corpus["publications"]
        ),
        "sourceReferenceDoiOccurrenceCount": sum(
            len(reference["occurrences"])
            for pub in corpus["publications"]
            for reference in pub["content"]["reference_dois"]
        ),
        "sourceAvailabilityIdentifierCount": sum(
            len(pub["content"]["availability_identifiers"])
            for pub in corpus["publications"]
        ),
        "nodeCount": len(nodes),
        "edgeCount": len(edges),
        "nodesByClass": _counter_dict(str(node["class"]) for node in nodes),
        "edgesByRelation": _counter_dict(str(edge["relation"]) for edge in edges),
        "edgesByInventoryId": _counter_dict(str(edge["inventoryId"]) for edge in edges),
        "curatedNodeCount": sum(node["curationStatus"] == CURATED for node in nodes),
        "referencedNodeCount": sum(node["curationStatus"] == REFERENCED for node in nodes),
        "citationRecordsProcessed": len(builder.citation_accounted),
        "citationSelfReferencesSkipped": sum(
            record["category"] == "self_reference_doi_matches_source"
            for record in builder.skipped
        ),
        "citationEdgesToCuratedPapers": sum(
            edge["relation"] == "cites"
            and bool(edge["attributes"].get("targetIsCurated"))
            for edge in citation_edges
        ),
        "citationEdgesToReferencedPapers": sum(
            edge["relation"] == "cites"
            and not bool(edge["attributes"].get("targetIsCurated"))
            for edge in citation_edges
        ),
        "citationDatasetReferences": sum(
            edge["relation"] == "referencesDataset" for edge in citation_edges
        ),
        "citationRepositoryTargets": len(citation_target_ids_by_class["Repository"]),
        "citationToolTargets": len(citation_target_ids_by_class["Tool"]),
        "citationTargetsDeferred": sum(
            record["category"] in citation_deferred_categories
            and str(record["phaseAField"]).startswith("content.reference_dois[")
            for record in reports
        ),
        "uniqueCitationTargetsByClass": {
            key: len(value) for key, value in sorted(citation_target_ids_by_class.items())
        },
        "availabilityRecordsProcessed": len(builder.availability_accounted),
        "availabilityDatasetResources": sum(
            nodes_by_id[edge["target"]]["class"] == "DatasetResource"
            for edge in uses_edges
        ),
        "availabilityDatasetMentions": sum(
            nodes_by_id[edge["target"]]["class"] == "DatasetMention"
            for edge in uses_edges
        ),
        "availabilityRepositoryTargets": sum(
            record["category"] == "paper_repository_relation_not_declared"
            and str(record["phaseAField"]).startswith(
                "content.availability_identifiers["
            )
            for record in builder.deferred
        ),
        "availabilityToolTargets": sum(
            record["category"] == "paper_tool_relation_requires_semantic_context"
            and str(record["phaseAField"]).startswith(
                "content.availability_identifiers["
            )
            for record in builder.deferred
        ),
        "availabilityDeferred": sum(
            record["category"] in availability_deferred_categories
            and str(record["phaseAField"]).startswith(
                "content.availability_identifiers["
            )
            for record in reports
        ),
        "deferredCount": len(builder.deferred),
        "skippedCount": len(builder.skipped),
        "unresolvedCount": len(builder.unresolved),
        "warningCount": len(builder.warnings),
        "warningsByCategory": _counter_dict(
            str(record["category"]) for record in builder.warnings
        ),
        "fieldDispositionCoverage": dict(sorted(FIELD_DISPOSITIONS.items())),
    }


def _base_occurrence_field(phase_a_field: str) -> str:
    """Collapse a citation occurrence field to its source record field."""
    return phase_a_field.split(".occurrences[", 1)[0]


def validate_field_coverage(corpus: Mapping[str, Any]) -> list[str]:
    """Validate that every current Phase A field group has a disposition."""
    issues: list[str] = []
    required_dispositions = {
        "schema_version",
        "phase_a_version",
        "source.*",
        "publications[]",
        "known_exclusions[]",
        "warnings[]",
        "summary",
        "local_paper_id",
        "canonical_artifact_id",
        "canonical_identifier",
        "identifiers[]",
        "record_type",
        "curation_status",
        "bibliographic.authors[]",
        "bibliographic.venue",
        "content.headings[]",
        "content.explicit_keywords[]",
        "content.reference_dois[]",
        "content.availability_identifiers[]",
        "document_structure.page_count",
        "document_structure.table_of_contents[]",
        "source_files.*",
        "bibliographic_relations.correction_of",
        "reconciliation.*",
    }
    required_dispositions.update(
        f"bibliographic.{field_name}"
        for field_name in BIBLIOGRAPHIC_FIELDS
        if field_name not in {"authors", "venue"}
    )
    missing = required_dispositions - set(FIELD_DISPOSITIONS)
    if missing:
        issues.append(f"Missing Phase A field dispositions: {sorted(missing)}")
    if set(corpus) != set(TOP_LEVEL_FIELDS):
        issues.append("Input top-level field coverage does not match the registered schema")
    return issues


def _accounted_source_fields(output: Mapping[str, Any]) -> tuple[set[tuple[str, str]], set[tuple[str, str]]]:
    """Reconstruct citation and availability dispositions from output facts."""
    citation: set[tuple[str, str]] = set()
    availability: set[tuple[str, str]] = set()
    for edge in output["edges"]:
        if edge["relation"] in {"cites", "referencesDataset"}:
            for declaration in edge["attributes"].get("sourceDeclarations", []):
                citation.add(
                    (
                        str(declaration["sourceArtifact"]),
                        _base_occurrence_field(str(declaration["phaseAField"])),
                    )
                )
        if edge["relation"] == "usesDataset":
            declarations = edge["attributes"].get("sourceDeclarations")
            if declarations:
                for declaration in declarations:
                    availability.add(
                        (
                            str(declaration["sourceArtifact"]),
                            str(declaration["phaseAField"]),
                        )
                    )
            else:
                availability.add(
                    (
                        str(edge["evidence"]["sourceArtifact"]),
                        str(edge["internalLineage"]["phaseAField"]),
                    )
                )
    for bucket in ("deferred", "skipped", "unresolved"):
        for record in output[bucket]:
            key = (str(record["publicationId"]), str(record["phaseAField"]))
            if str(record["phaseAField"]).startswith("content.reference_dois["):
                citation.add(key)
            if str(record["phaseAField"]).startswith(
                "content.availability_identifiers["
            ):
                availability.add(key)
    return citation, availability


def validate_output(
    output: Mapping[str, Any],
    corpus: Mapping[str, Any],
    ontology: OntologyRegistry,
    *,
    validate_frozen_snapshot: bool = False,
) -> list[str]:
    """Validate structural, ontology, identity, coverage, and provenance rules."""
    issues: list[str] = []
    expected_top = {
        "schema_version",
        "phase_b_version",
        "source_schema_version",
        "source_phase_a_version",
        "source_type",
        "nodes",
        "edges",
        "deferred",
        "skipped",
        "unresolved",
        "warnings",
        "stats",
    }
    if set(output) != expected_top:
        issues.append("Output top-level shape differs from the contract")
    expected_versions = {
        "schema_version": OUTPUT_SCHEMA_VERSION,
        "phase_b_version": PHASE_B_VERSION,
        "source_schema_version": corpus["schema_version"],
        "source_phase_a_version": corpus["phase_a_version"],
        "source_type": SOURCE_TYPE,
    }
    for key, expected in expected_versions.items():
        if output.get(key) != expected:
            issues.append(f"{key}={output.get(key)!r}, expected {expected!r}")

    nodes = output.get("nodes", [])
    edges = output.get("edges", [])
    source_artifacts = {
        str(publication["canonical_artifact_id"])
        for publication in corpus["publications"]
    }
    expected_evidence_version = f"phase-a:{corpus['phase_a_version']}"
    if not isinstance(nodes, list) or not isinstance(edges, list):
        return [*issues, "nodes and edges must be arrays"]
    if nodes != sorted(nodes, key=lambda item: item["id"]):
        issues.append("Nodes are not sorted by ID")
    if edges != sorted(edges, key=lambda item: item["id"]):
        issues.append("Edges are not sorted by ID")
    node_ids: set[str] = set()
    nodes_by_id: dict[str, Mapping[str, Any]] = {}
    doi_target_classes: dict[str, set[str]] = defaultdict(set)
    exact_keys: dict[tuple[str, str], str] = {}
    for index, node in enumerate(nodes):
        if set(node) != set(NODE_REQUIRED_KEYS):
            issues.append(f"nodes[{index}] has invalid shape")
            continue
        node_id = str(node["id"])
        if node_id in node_ids:
            issues.append(f"Duplicate node ID {node_id}")
        node_ids.add(node_id)
        nodes_by_id[node_id] = node
        try:
            ontology.class_entry(str(node["class"]), str(node["inventoryId"]))
        except ValueError as exc:
            issues.append(str(exc))
        if node["curationStatus"] not in {CURATED, REFERENCED}:
            issues.append(f"Invalid curationStatus on {node_id}")
        if set(node.get("evidence", {})) != set(EVIDENCE_REQUIRED_KEYS) or not all(
            node.get("evidence", {}).get(key) not in (None, "")
            for key in EVIDENCE_REQUIRED_KEYS
        ):
            issues.append(f"Node {node_id} lacks complete evidence")
        if not isinstance(node.get("internalLineage"), Mapping) or not node["internalLineage"]:
            issues.append(f"Node {node_id} lacks internal lineage")
        if str(node["canonicalKey"]).startswith("doi:") and node["class"] in {
            "Paper",
            "DatasetResource",
            "Repository",
            "Tool",
        }:
            doi_target_classes[str(node["canonicalKey"])].add(str(node["class"]))
        if node["class"] in {"Venue", "Subject", "Identifier"}:
            key = (str(node["class"]), str(node["canonicalKey"]))
            if key in exact_keys and exact_keys[key] != node_id:
                issues.append(f"Duplicate exact entity key {key}")
            exact_keys[key] = node_id
        evidence = node["evidence"]
        if evidence.get("extractionMethod") != EXTRACTION_METHOD:
            issues.append(f"Node {node_id} has invalid extraction method")
        if evidence.get("version") != expected_evidence_version:
            issues.append(f"Node {node_id} has invalid evidence version")
        if evidence.get("sourceArtifact") not in source_artifacts:
            issues.append(f"Node {node_id} evidence does not identify a source publication")
        if evidence.get("sourceArtifact") != evidence.get("sourceLocation"):
            issues.append(f"Node {node_id} public evidence invents a distinct location")
        if not normalize_url(evidence.get("sourceArtifact")):
            issues.append(f"Node {node_id} public evidence is not an absolute URL")

    for key, classes in doi_target_classes.items():
        if len(classes) > 1:
            issues.append(f"DOI target {key} assigned to multiple classes {sorted(classes)}")

    strong_decision_by_class = {
        "DatasetResource": "strong_dataset",
        "Repository": "strong_repository",
        "Tool": "strong_tool",
    }
    valid_occurrence_decisions = {
        "curated_paper",
        "untyped_scholarly_reference",
        "strong_dataset",
        "strong_repository",
        "strong_tool",
        "ambiguous",
        "conflicting",
    }
    for node in nodes:
        if node.get("class") not in {"Paper", "DatasetResource", "Repository", "Tool"}:
            continue
        declarations = [
            declaration
            for declaration in node.get("attributes", {}).get("sourceDeclarations", [])
            if str(declaration.get("phaseAField", "")).startswith(
                "content.reference_dois["
            )
        ]
        for declaration in declarations:
            if declaration.get("occurrenceDecision") not in valid_occurrence_decisions:
                issues.append(
                    f"Citation target {node['id']} lacks a valid occurrence decision"
                )
        expected_strong = strong_decision_by_class.get(str(node.get("class")))
        if declarations and expected_strong and not any(
            declaration.get("occurrenceDecision") == expected_strong
            for declaration in declarations
        ):
            issues.append(
                f"Non-Paper citation target {node['id']} lacks strong occurrence evidence"
            )

    edge_ids: set[str] = set()
    for index, edge in enumerate(edges):
        if set(edge) != set(EDGE_REQUIRED_KEYS):
            issues.append(f"edges[{index}] has invalid shape")
            continue
        edge_id = str(edge["id"])
        if edge_id in edge_ids:
            issues.append(f"Duplicate edge ID {edge_id}")
        edge_ids.add(edge_id)
        source = nodes_by_id.get(str(edge["source"]))
        target = nodes_by_id.get(str(edge["target"]))
        if source is None or target is None:
            issues.append(f"Dangling edge {edge_id}")
            continue
        try:
            ontology.validate_edge(
                str(edge["relation"]),
                str(edge["inventoryId"]),
                str(source["class"]),
                str(target["class"]),
            )
        except ValueError as exc:
            issues.append(str(exc))
        if edge["source"] == edge["target"] and edge["relation"] == "cites":
            issues.append(f"Citation self-loop {edge_id}")
        if edge["relation"] == "referencesDataset" and edge["inventoryId"] != "C-P29":
            issues.append(f"Dataset citation {edge_id} does not use C-P29")
        if set(edge.get("evidence", {})) != set(EVIDENCE_REQUIRED_KEYS) or not all(
            edge.get("evidence", {}).get(key) not in (None, "")
            for key in EVIDENCE_REQUIRED_KEYS
        ):
            issues.append(f"Edge {edge_id} lacks complete evidence")
        if not isinstance(edge.get("internalLineage"), Mapping) or not edge["internalLineage"]:
            issues.append(f"Edge {edge_id} lacks internal lineage")
        evidence = edge["evidence"]
        if evidence.get("extractionMethod") != EXTRACTION_METHOD:
            issues.append(f"Edge {edge_id} has invalid extraction method")
        if evidence.get("version") != expected_evidence_version:
            issues.append(f"Edge {edge_id} has invalid evidence version")
        if evidence.get("sourceArtifact") not in source_artifacts:
            issues.append(f"Edge {edge_id} evidence does not identify a source publication")
        if evidence.get("sourceArtifact") != evidence.get("sourceLocation"):
            issues.append(f"Edge {edge_id} public evidence invents a distinct location")
        if not normalize_url(evidence.get("sourceArtifact")):
            issues.append(f"Edge {edge_id} public evidence is not an absolute URL")

    for bucket in ("deferred", "skipped", "unresolved", "warnings"):
        records = output.get(bucket, [])
        if records != sorted(records, key=report_sort_key):
            issues.append(f"{bucket} records are not deterministically sorted")
        for index, record in enumerate(records):
            expected_report_keys = {
                "publicationId",
                "category",
                "phaseAField",
                "reason",
                "value",
                "sourceLine",
            }
            if set(record) != expected_report_keys:
                issues.append(f"{bucket}[{index}] has invalid report shape")
    if any(
        record.get("category") == "availability_identifier_already_typed_paper"
        for record in output.get("deferred", [])
    ):
        issues.append(
            "Availability was incorrectly subordinated to a Paper citation target"
        )

    for path, text in _walk_strings(output):
        if FORBIDDEN_CONTROL_RE.search(text):
            issues.append(f"Forbidden control character at {path}")
            break
    public_evidence = [node["evidence"] for node in nodes] + [
        edge["evidence"] for edge in edges
    ]
    for evidence in public_evidence:
        serialized = stable_json(evidence)
        if "data/raw/" in serialized or "markdowns/" in serialized:
            issues.append("Local path appears in public evidence")
            break

    expected_citation = {
        (
            str(publication["canonical_artifact_id"]),
            f"content.reference_dois[{index}]",
        )
        for publication in corpus["publications"]
        for index, _ in enumerate(publication["content"]["reference_dois"])
    }
    expected_availability = {
        (
            str(publication["canonical_artifact_id"]),
            f"content.availability_identifiers[{index}]",
        )
        for publication in corpus["publications"]
        for index, _ in enumerate(publication["content"]["availability_identifiers"])
    }
    actual_citation, actual_availability = _accounted_source_fields(output)
    if actual_citation != expected_citation:
        issues.append(
            "Citation source accounting differs: "
            f"missing={len(expected_citation - actual_citation)} "
            f"extra={len(actual_citation - expected_citation)}"
        )
    if actual_availability != expected_availability:
        issues.append(
            "Availability source accounting differs: "
            f"missing={len(expected_availability - actual_availability)} "
            f"extra={len(actual_availability - expected_availability)}"
        )
    issues.extend(validate_field_coverage(corpus))

    curated_papers = [
        node for node in nodes if node["class"] == "Paper" and node["curationStatus"] == CURATED
    ]
    expected_counts = {
        "curated Paper nodes": (len(curated_papers), len(corpus["publications"])),
        "Person nodes": (
            sum(node["class"] == "Person" for node in nodes),
            sum(len(pub["bibliographic"]["authors"]) for pub in corpus["publications"]),
        ),
        "hasAuthor edges": (
            sum(edge["relation"] == "hasAuthor" for edge in edges),
            sum(len(pub["bibliographic"]["authors"]) for pub in corpus["publications"]),
        ),
        "publishedIn edges": (
            sum(edge["relation"] == "publishedIn" for edge in edges),
            len(corpus["publications"]),
        ),
        "hasSubject edges": (
            sum(edge["relation"] == "hasSubject" for edge in edges),
            sum(len(pub["content"]["explicit_keywords"]) for pub in corpus["publications"]),
        ),
        "curated Paper hasIdentifier edges": (
            sum(
                edge["relation"] == "hasIdentifier"
                and nodes_by_id[edge["source"]]["class"] == "Paper"
                for edge in edges
            ),
            sum(len(pub["identifiers"]) for pub in corpus["publications"]),
        ),
        "corrects edges": (
            sum(edge["relation"] == "corrects" for edge in edges),
            sum(
                pub["bibliographic_relations"]["correction_of"] is not None
                for pub in corpus["publications"]
            ),
        ),
    }
    for label, (actual, expected) in expected_counts.items():
        if actual != expected:
            issues.append(f"{label}={actual}, expected {expected}")
    person_sources = {
        (
            node["internalLineage"].get("localPaperId"),
            node["attributes"].get("authorPosition"),
        )
        for node in nodes
        if node["class"] == "Person"
    }
    if len(person_sources) != expected_counts["Person nodes"][1]:
        issues.append("Author mentions were consolidated or positions were lost")

    stats = output.get("stats", {})
    actual_stats = {
        "nodeCount": len(nodes),
        "edgeCount": len(edges),
        "nodesByClass": _counter_dict(str(node["class"]) for node in nodes),
        "edgesByRelation": _counter_dict(str(edge["relation"]) for edge in edges),
        "deferredCount": len(output["deferred"]),
        "skippedCount": len(output["skipped"]),
        "unresolvedCount": len(output["unresolved"]),
        "warningCount": len(output["warnings"]),
    }
    for key, expected in actual_stats.items():
        if stats.get(key) != expected:
            issues.append(f"stats.{key} does not reconcile with output arrays")
    if stats.get("citationRecordsProcessed") != len(expected_citation):
        issues.append("stats.citationRecordsProcessed does not reconcile")
    expected_occurrences = sum(
        len(reference["occurrences"])
        for publication in corpus["publications"]
        for reference in publication["content"]["reference_dois"]
    )
    if stats.get("sourceReferenceDoiOccurrenceCount") != expected_occurrences:
        issues.append("stats.sourceReferenceDoiOccurrenceCount does not reconcile")
    if stats.get("availabilityRecordsProcessed") != len(expected_availability):
        issues.append("stats.availabilityRecordsProcessed does not reconcile")
    if len(output["warnings"]) != (
        len(corpus["warnings"])
        + sum(len(pub["reconciliation"]["warnings"]) for pub in corpus["publications"])
        + sum(len(pub["reconciliation"]["conflicts"]) for pub in corpus["publications"])
    ):
        issues.append("Phase A warnings or conflicts were not propagated exactly")
    if sum(record["category"] == "known_phase_a_exclusion" for record in output["skipped"]) != len(corpus["known_exclusions"]):
        issues.append("Known Phase A exclusions were not propagated exactly")

    if validate_frozen_snapshot:
        frozen = {
            "curated Paper nodes": (len(curated_papers), 228),
            "Person nodes": (sum(node["class"] == "Person" for node in nodes), 1602),
            "Venue nodes": (sum(node["class"] == "Venue" for node in nodes), 84),
            "Subject nodes": (sum(node["class"] == "Subject" for node in nodes), 317),
            "hasAuthor edges": (sum(edge["relation"] == "hasAuthor" for edge in edges), 1602),
            "publishedIn edges": (sum(edge["relation"] == "publishedIn" for edge in edges), 228),
            "hasSubject edges": (sum(edge["relation"] == "hasSubject" for edge in edges), 373),
            "curated identifiers": (expected_counts["curated Paper hasIdentifier edges"][0], 455),
            "corrects edges": (sum(edge["relation"] == "corrects" for edge in edges), 1),
            "source reference DOI records": (
                stats.get("sourceReferenceDoiCount"),
                8856,
            ),
            "source reference DOI occurrences": (
                stats.get("sourceReferenceDoiOccurrenceCount"),
                8963,
            ),
            "source availability records": (
                stats.get("sourceAvailabilityIdentifierCount"),
                299,
            ),
            "self references": (
                sum(record["category"] == "self_reference_doi_matches_source" for record in output["skipped"]),
                23,
            ),
        }
        for label, (actual, expected) in frozen.items():
            if actual != expected:
                issues.append(f"Frozen output {label}={actual}, expected {expected}")
    return issues


def extract_corpus(
    corpus: Mapping[str, Any],
    ontology: OntologyRegistry,
    *,
    source_corpus_sha256: str,
    validate_frozen_snapshot: bool = False,
) -> JsonObject:
    """Transform one validated Phase A corpus into deterministic Phase B output."""
    input_issues = validate_input(corpus, validate_frozen_snapshot)
    if input_issues:
        raise InputValidationError(input_issues)
    builder = GraphBuilder(str(corpus["phase_a_version"]), ontology)
    contexts, doi_index = emit_curated_backbone(corpus, builder)
    citation_registry = build_global_citation_target_registry(
        contexts, set(doi_index)
    )
    process_citations(contexts, doi_index, citation_registry, builder)
    process_availability(contexts, citation_registry, builder)
    process_corrections(contexts, doi_index, builder)
    propagate_phase_a_reports(corpus, builder)
    finalize_source_declarations(builder.nodes.values())
    finalize_source_declarations(builder.edges.values())
    output: JsonObject = {
        "schema_version": OUTPUT_SCHEMA_VERSION,
        "phase_b_version": PHASE_B_VERSION,
        "source_schema_version": corpus["schema_version"],
        "source_phase_a_version": corpus["phase_a_version"],
        "source_type": SOURCE_TYPE,
        "nodes": sorted(builder.nodes.values(), key=lambda item: item["id"]),
        "edges": sorted(builder.edges.values(), key=lambda item: item["id"]),
        "deferred": sorted(builder.deferred, key=report_sort_key),
        "skipped": sorted(builder.skipped, key=report_sort_key),
        "unresolved": sorted(builder.unresolved, key=report_sort_key),
        "warnings": sorted(builder.warnings, key=report_sort_key),
        "stats": {},
    }
    output["stats"] = build_stats(corpus, builder, source_corpus_sha256)
    output_issues = validate_output(
        output,
        corpus,
        ontology,
        validate_frozen_snapshot=validate_frozen_snapshot,
    )
    if output_issues:
        raise OutputValidationError(output_issues)
    serialized = serialize_deterministically(output)
    reparsed = json.loads(serialized.decode("utf-8"))
    if serialized != serialize_deterministically(reparsed):
        raise OutputValidationError(
            ["Canonical serialize/parse/reserialize validation failed"]
        )
    return output


def load_json(path: Path) -> tuple[JsonObject, str]:
    """Load UTF-8 JSON and return its SHA-256 digest."""
    raw = path.read_bytes()
    return json.loads(raw.decode("utf-8")), sha256_bytes(raw)


def load_ontology(path: Path) -> OntologyRegistry:
    """Load and validate the machine-readable ontology registry."""
    spec = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(spec, Mapping):
        raise ValueError("Ontology specification must be a mapping")
    return OntologyRegistry(spec)


def write_atomically(path: Path, payload: bytes) -> None:
    """Replace an output only after extraction and validation have succeeded."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")
    try:
        temporary.write_bytes(payload)
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


def build_argument_parser() -> argparse.ArgumentParser:
    """Create the Publication Phase B command-line parser."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--ontology-spec", type=Path, default=DEFAULT_ONTOLOGY_SPEC)
    parser.add_argument("--validate-frozen-snapshot", action="store_true")
    parser.add_argument(
        "--log-level",
        choices=("DEBUG", "INFO", "WARNING", "ERROR"),
        default="INFO",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run the offline deterministic Publication Phase B extraction."""
    args = build_argument_parser().parse_args(argv)
    logging.basicConfig(level=getattr(logging, args.log_level), format="%(levelname)s: %(message)s")
    try:
        corpus, source_hash = load_json(args.input)
        ontology = load_ontology(args.ontology_spec)
        output = extract_corpus(
            corpus,
            ontology,
            source_corpus_sha256=source_hash,
            validate_frozen_snapshot=args.validate_frozen_snapshot,
        )
        payload = serialize_deterministically(output)
        write_atomically(args.output, payload)
    except (OSError, json.JSONDecodeError, yaml.YAMLError, ValueError) as exc:
        logging.error("%s", exc)
        return 1
    stats = output["stats"]
    logging.info(
        "Publication Phase B valid: %s publications, %s nodes, %s edges",
        stats["sourcePublicationCount"],
        stats["nodeCount"],
        stats["edgeCount"],
    )
    logging.info(
        "Reports: deferred=%s skipped=%s unresolved=%s warnings=%s",
        stats["deferredCount"],
        stats["skippedCount"],
        stats["unresolvedCount"],
        stats["warningCount"],
    )
    logging.info("Output: %s", args.output)
    logging.info("SHA-256: %s", sha256_bytes(payload))
    return 0


if __name__ == "__main__":
    sys.exit(main())
