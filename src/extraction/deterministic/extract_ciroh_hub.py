"""Extract deterministic CIROH Hub ontology mentions from the Phase A corpus.

This offline Phase B transformer reads only the consolidated, page-centric
CIROH Hub corpus. It emits deterministic mention-level nodes, declared edges,
inline EvidenceSpan records, and extraction dispositions. It does not reopen
raw documents, execute MDX, make network calls, call an LLM, perform fuzzy
matching, or infer product and procedural semantics from prose.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import unicodedata
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath
from typing import Any, Iterable, Mapping, Sequence
from urllib.parse import quote, unquote, urlsplit

import yaml


PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_INPUT = PROJECT_ROOT / "data/interim/documents/ciroh_hub_corpus.json"
DEFAULT_OUTPUT = PROJECT_ROOT / "data/interim/documents/ciroh_hub_nodes_edges.json"
DEFAULT_ONTOLOGY_SPEC = PROJECT_ROOT / "src/ontology/ontology_spec.yaml"
DEFAULT_SOURCE_REPOSITORY_URL = "https://github.com/CIROH-UA/ciroh_hub"
DEFAULT_SOURCE_REPOSITORY_REF = "main"

OUTPUT_SCHEMA_VERSION = "1.0.0"
PHASE_B_VERSION = "1.0.0"
SUPPORTED_SOURCE_SCHEMAS = frozenset({"1.0.0"})
SUPPORTED_PHASE_A_VERSIONS = frozenset({"1.0.2"})
SOURCE_TYPE = "ciroh_hub"
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

# Executable bindings from the CIROH Hub extraction mapping. These are not a
# duplicate ontology registry: each ID identifies the module-specific inventory
# rule that authorizes an emitted class or relation. Formal relation names may
# intentionally occur under multiple inventory IDs in the ontology.
HUB_NODE_RULE_IDS = {
    "DocumentationPage": "A-DC01",
    "Section": "A-DC02",
    "Link": "A-DC03",
    "Subject": "A-P04",
    "Person": "A-AG01",
    "Organization": "A-AG02",
    "Identifier": "A-ID01",
    "RepoFile": "A-C02",
    "Repository": "A-C01",
    "DatasetResource": "A-D01",
}
HUB_RELATION_RULE_IDS = {
    "hasIdentifier": "ID-R1",
    "hasSection": "C-DC01",
    "linksTo": "C-DC03",
    "hasSubject": "C-DC04",
    "hasContributor": "C-DC05",
    "hasSourceFile": "C-DC06",
    "affiliatedWith": "A-AG-R1",
    "isPartOf": "C-DC02",
    "hasSubPage": "C-DC02i",
    "hasFile": "C-C01",
    "documents": "C-DC13",
    "referencesRepository": "C-DC14",
    "referencesDataset": "C-DC15",
    "announces": "C-DC18",
}
FORBIDDEN_NODE_CLASSES = frozenset(
    {
        "Procedure",
        "Step",
        "Example",
        "Workflow",
        "Tool",
        "ComputationalModel",
        "Concept",
        "Parameter",
        "Algorithm",
    }
)
FORBIDDEN_RELATIONS = frozenset(
    {
        "describesTool",
        "describesModel",
        "mentionsConcept",
        "explainsWorkflow",
        "hasProcedure",
        "hasStep",
        "hasParameter",
        "hasExample",
        "catalogs",
        "hasComponent",
        "implementedBy",
        "describedInPaper",
        "documentedBy",
        "references",
    }
)

TOP_LEVEL_FIELDS = frozenset(
    {"schema_version", "phase_a_version", "source", "pages", "known_exclusions", "warnings", "summary"}
)
SOURCE_FIELDS = frozenset({"artifact_type", "base_url", "raw_root"})
PAGE_FIELDS = frozenset(
    {
        "page_key",
        "canonical_url",
        "path",
        "slug",
        "title",
        "title_source",
        "description",
        "last_updated_date",
        "last_updated_date_raw",
        "source_group",
        "corpus_path",
        "source_path",
        "generated_from_js",
        "front_matter",
        "tags",
        "authors",
        "content_mdx",
        "headings",
        "links",
        "external_content_sources",
        "parent_url",
        "file_sha256",
        "content_sha256",
        "warnings",
    }
)
HEADING_FIELDS = frozenset(
    {"ordinal", "level", "text", "raw_text", "source_line", "parent_heading_ordinal"}
)
LINK_FIELDS = frozenset(
    {"ordinal", "anchor_text", "raw_target", "resolved_url", "link_type", "source_line", "heading_ordinal"}
)
AUTHOR_FIELDS = frozenset({"name", "role", "affiliation", "url", "source"})
EXTERNAL_SOURCE_FIELDS = frozenset(
    {"component", "username", "repository", "path", "source_line", "ordinal"}
)
WARNING_FIELDS = frozenset({"file", "issue", "detail"})
KNOWN_EXCLUSION_FIELDS = frozenset({"route", "source_path", "reason"})
SUMMARY_FIELDS = frozenset(
    {
        "by_source_group",
        "exclusions_by_rule",
        "generated_from_js",
        "page_warning_count",
        "top_level_warning_count",
        "total_external_content_sources",
        "total_headings",
        "total_links",
        "total_pages",
        "with_authors",
        "with_external_content",
        "with_parent_url",
        "with_tags",
        "with_title_fallback",
    }
)

DOI_RE = re.compile(r"^10\.\d{4,9}/\S+$", re.IGNORECASE)
HYDROSHARE_PATH_RE = re.compile(r"(?:^|/)resource/([0-9a-f]{32})(?:/|$)", re.IGNORECASE)
ORCID_RE = re.compile(r"(?:https?://orcid\.org/)?(\d{4}-\d{4}-\d{4}-\d{3}[\dX])", re.IGNORECASE)
IMAGE_SUFFIXES = (".svg", ".png", ".jpg", ".jpeg", ".gif", ".webp")
GITHUB_RESERVED_FIRST_SEGMENTS = frozenset(
    {"about", "apps", "collections", "contact", "enterprise", "events", "features", "login", "marketplace", "new", "organizations", "orgs", "pricing", "search", "settings", "site", "sponsors", "topics", "users"}
)
GITHUB_RESERVED_REPOSITORY_ROUTES = frozenset(
    {"login", "marketplace", "search", "settings"}
)

JsonObject = dict[str, Any]


def stable_json(value: Any) -> str:
    """Serialize a JSON-compatible value canonically for sorting and hashing."""
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def stable_hash(value: str) -> str:
    """Return the first 20 lowercase hexadecimal characters of SHA-256."""
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:20]


def sha256_bytes(value: bytes) -> str:
    """Return the complete lowercase SHA-256 digest for bytes."""
    return hashlib.sha256(value).hexdigest()


def sorted_unique(values: Iterable[Any]) -> list[Any]:
    """Return JSON-distinct values in canonical deterministic order."""
    distinct = {stable_json(value): value for value in values}
    return [distinct[key] for key in sorted(distinct)]


def nonempty_text(value: Any) -> str:
    """Convert a value to stable evidence text without Python representations."""
    if isinstance(value, str):
        return value.strip()
    if value is None:
        return ""
    return stable_json(value)


def normalize_text_key(value: str | None) -> str:
    """Apply NFKC, whitespace collapse, and case folding for exact text keys."""
    normalized = unicodedata.normalize("NFKC", str(value or ""))
    return " ".join(normalized.split()).casefold()


def normalize_hub_url(value: str | None) -> str | None:
    """Normalize an exact CIROH Hub URL for target matching without double decoding."""
    if not value:
        return None
    parsed = urlsplit(str(value).strip())
    if parsed.scheme.casefold() not in {"http", "https"} or parsed.hostname and parsed.hostname.casefold() != "hub.ciroh.org":
        return None
    if not parsed.hostname or parsed.hostname.casefold() != "hub.ciroh.org":
        return None
    path = parsed.path or "/"
    return f"https://hub.ciroh.org{path}"


def build_hub_page_alias_index(pages: Sequence[Mapping[str, Any]]) -> dict[str, str]:
    """Build exact and unambiguous terminal-slash aliases for curated Hub pages."""
    canonical_urls = {str(page["canonical_url"]) for page in pages}
    index = {url: url for url in canonical_urls}
    candidates: dict[str, set[str]] = defaultdict(set)
    for url in canonical_urls:
        alias = url[:-1] if url.endswith("/") and url != "https://hub.ciroh.org/" else url + "/"
        candidates[alias].add(url)
    for alias, targets in candidates.items():
        if alias not in index and len(targets) == 1:
            index[alias] = next(iter(targets))
    return index


def normalize_github_repo_url(value: str | None) -> str | None:
    """Normalize a valid GitHub repository URL, including declared repository subpaths."""
    if not value:
        return None
    raw = str(value).strip().removeprefix("git+")
    if raw.startswith("git@github.com:"):
        raw = "https://github.com/" + raw.removeprefix("git@github.com:")
    elif raw.startswith("ssh://git@github.com/"):
        raw = "https://github.com/" + raw.removeprefix("ssh://git@github.com/")
    parsed = urlsplit(raw)
    if parsed.scheme.casefold() not in {"http", "https"} or parsed.hostname and parsed.hostname.casefold() not in {"github.com", "www.github.com"}:
        return None
    if not parsed.hostname or parsed.hostname.casefold() not in {"github.com", "www.github.com"}:
        return None
    parts = [unquote(part) for part in parsed.path.strip("/").split("/") if part]
    if len(parts) < 2 or parts[0].casefold() in GITHUB_RESERVED_FIRST_SEGMENTS:
        return None
    if parsed.path.casefold().endswith(IMAGE_SUFFIXES):
        return None
    owner, repository = parts[:2]
    if repository.casefold() in {"settings", "people", "repositories", ".", ".."}:
        return None
    repository = repository[:-4] if repository.casefold().endswith(".git") else repository
    if not owner or not repository or any("/" in item for item in (owner, repository)):
        return None
    if len(parts) >= 3 and parts[2].casefold() in GITHUB_RESERVED_REPOSITORY_ROUTES:
        return None
    return f"https://github.com/{owner}/{repository}"


def parse_github_pull_request(value: str | None) -> tuple[str, int] | None:
    """Return the exact GitHub repository root and PR number for a pull-request URL."""
    root = normalize_github_repo_url(value)
    if not root or not value:
        return None
    parts = [unquote(part) for part in urlsplit(str(value).strip()).path.strip("/").split("/") if part]
    if len(parts) >= 4 and parts[2].casefold() == "pull" and parts[3].isdigit():
        return root, int(parts[3])
    return None


def github_login_from_profile(value: str | None) -> str | None:
    """Extract a GitHub login only from an exact one-segment public profile URL."""
    if not value:
        return None
    parsed = urlsplit(str(value).strip())
    if parsed.hostname and parsed.hostname.casefold() in {"github.com", "www.github.com"}:
        parts = [unquote(part) for part in parsed.path.strip("/").split("/") if part]
        if len(parts) == 1 and parts[0].casefold() not in GITHUB_RESERVED_FIRST_SEGMENTS:
            return parts[0]
    return None


def extract_hydroshare_resource_id(value: str | None) -> str | None:
    """Extract an exact lowercase HydroShare resource identifier from a supported URL."""
    if not value:
        return None
    parsed = urlsplit(str(value).strip())
    host = (parsed.hostname or "").casefold()
    if parsed.scheme.casefold() not in {"http", "https"} or not (host == "hydroshare.org" or host.endswith(".hydroshare.org")):
        return None
    match = HYDROSHARE_PATH_RE.search(parsed.path)
    return match.group(1).lower() if match else None


def normalize_doi(value: str | None) -> str | None:
    """Normalize a DOI for deferred typing and reject obvious image/badge targets."""
    if not value:
        return None
    raw = unquote(str(value).strip())
    lowered = raw.casefold()
    if "shields.io" in lowered or "/badge/" in lowered or lowered.endswith(IMAGE_SUFFIXES):
        return None
    raw = re.sub(r"^doi:\s*", "", raw, flags=re.IGNORECASE)
    raw = re.sub(r"^https?://(?:dx\.)?doi\.org/", "", raw, flags=re.IGNORECASE)
    normalized = raw.rstrip(".,;:)]}").casefold()
    return normalized if DOI_RE.fullmatch(normalized) else None


def encode_repository_path(source_path: str) -> str:
    """Segment-encode a safe repository-relative path while preserving slash and case."""
    pure_path = PurePosixPath(source_path)
    if not source_path or source_path.startswith("/") or ".." in pure_path.parts:
        raise ValueError(f"Unsafe repository-relative source path: {source_path!r}")
    return "/".join(quote(part, safe="") for part in pure_path.parts)


def build_source_blob_url(repository_url: str, repository_ref: str, source_path: str) -> str:
    """Construct a public source-file URL without checking it over the network."""
    encoded_ref = quote(repository_ref, safe="/")
    return f"{repository_url.rstrip('/')}/blob/{encoded_ref}/{encode_repository_path(source_path)}"


def derive_page_type(page: Mapping[str, Any]) -> str | None:
    """Apply the contract's priority-ordered path/source page-type mapping."""
    source_group = str(page.get("source_group") or "")
    corpus_path = str(page.get("corpus_path") or "")
    canonical_url = str(page.get("canonical_url") or "")
    if source_group == "blog":
        return "blog-post"
    if source_group == "release_notes":
        return "release-note"
    if corpus_path.startswith("docs/policies/"):
        return "policy"
    if corpus_path.startswith("docs/services/"):
        return "service-doc"
    if corpus_path == "docs/products/intro.mdx":
        return "product-catalog"
    if corpus_path.startswith("docs/products/"):
        return "product-doc"
    if corpus_path.startswith("docs/contribute/"):
        return "guide"
    if source_group == "generated_js_page" and canonical_url in {
        "https://hub.ciroh.org/contribute",
        "https://hub.ciroh.org/contribute/develop",
    }:
        return "guide"
    if corpus_path == "src/pages/news.mdx":
        return "news"
    return None


def make_page_id(canonical_url: str) -> str:
    """Return the contract ID for a curated Hub page."""
    return f"hub:page:{stable_hash(canonical_url)}"


def make_section_id(canonical_url: str, ordinal: int) -> str:
    """Return a page-scoped heading occurrence ID."""
    return f"hub:section:{stable_hash(canonical_url)}:{ordinal:04d}"


def make_link_id(canonical_url: str, ordinal: int) -> str:
    """Return a page-scoped link occurrence ID."""
    return f"hub:link:{stable_hash(canonical_url)}:{ordinal:04d}"


def make_source_file_id(repository_url: str, source_path: str) -> str:
    """Return the exact configured-repository source-file ID."""
    return f"hub:source-file:{stable_hash(f'{repository_url}|{source_path}') }"


def make_exact_identifier_id(id_type: str, normalized_value: str) -> str:
    """Return a deterministic exact Identifier ID."""
    return f"hub:identifier:{stable_hash(f'{id_type}|{normalized_value}') }"


def make_edge_id(source: str, relation: str, target: str, qualifier: str = "") -> str:
    """Return a deterministic edge ID from semantic identity and optional occurrence scope."""
    discriminator = f"{source}|{relation}|{target}"
    if qualifier:
        discriminator += f"|{qualifier}"
    return f"hub:edge:{relation}:{stable_hash(discriminator)}"


def make_evidence(
    _owner_id: str,
    evidence_text: Any,
    source_location: str,
    source_artifact: str,
    version: Any,
) -> JsonObject:
    """Build one deterministic inline EvidenceSpan-compatible record."""
    return {
        "evidenceText": nonempty_text(evidence_text),
        "sourceLocation": source_location,
        "extractionMethod": EXTRACTION_METHOD,
        "sourceArtifact": source_artifact,
        "version": version,
    }


def make_lineage(
    phase_a_version: str,
    phase_a_field: str,
    page: Mapping[str, Any] | None = None,
    source_line: int | None = None,
    source_ordinal: int | None = None,
) -> JsonObject:
    """Build internal Phase A lineage without exposing it as public evidence."""
    lineage: JsonObject = {"phaseAField": phase_a_field, "phaseAVersion": phase_a_version}
    if page is not None:
        lineage["corpusPath"] = page["corpus_path"]
        lineage["sourcePath"] = page["source_path"]
    if source_line is not None:
        lineage["sourceLine"] = source_line
    if source_ordinal is not None:
        lineage["sourceOrdinal"] = source_ordinal
    return lineage


def declaration_sort_key(declaration: Mapping[str, Any]) -> tuple[int, int, str, str]:
    """Return the contract ordering for exact semantic source declarations."""
    source_line = declaration.get("sourceLine")
    source_ordinal = declaration.get("sourceOrdinal")
    return (
        int(source_line) if isinstance(source_line, int) else 10**9,
        int(source_ordinal) if isinstance(source_ordinal, int) else 10**9,
        str(declaration.get("rawTarget") or declaration.get("path") or ""),
        str(declaration.get("pageUrl") or ""),
    )


def select_primary_declaration(
    declarations: Sequence[Mapping[str, Any]],
) -> tuple[JsonObject, list[JsonObject]]:
    """Select primary evidence and return all declarations in stable order."""
    if not declarations:
        raise ValueError("At least one source declaration is required")
    ordered = [dict(item) for item in sorted(declarations, key=declaration_sort_key)]
    return ordered[0], ordered


@dataclass(frozen=True)
class OntologyRegistry:
    """Machine-readable class and relation definitions used for validation."""

    classes_by_id: Mapping[str, Mapping[str, Any]]
    relations_by_id: Mapping[str, Mapping[str, Any]]
    version: str
    sha256: str


def validate_hub_rule_bindings(
    ontology: OntologyRegistry,
    node_rule_ids: Mapping[str, str] | None = None,
    relation_rule_ids: Mapping[str, str] | None = None,
) -> None:
    """Validate Hub mapping bindings against authoritative ontology entries."""
    node_bindings = HUB_NODE_RULE_IDS if node_rule_ids is None else node_rule_ids
    relation_bindings = HUB_RELATION_RULE_IDS if relation_rule_ids is None else relation_rule_ids
    for class_name, inventory_id in node_bindings.items():
        definition = ontology.classes_by_id.get(inventory_id)
        if definition is None:
            raise ValueError(
                f"CIROH Hub node rule {class_name!r} uses unknown ontology inventory ID {inventory_id!r}"
            )
        actual_name = definition.get("name")
        if actual_name != class_name:
            raise ValueError(
                f"CIROH Hub node rule {class_name!r} binds to {inventory_id!r}, "
                f"whose ontology name is {actual_name!r}"
            )
    for relation_name, inventory_id in relation_bindings.items():
        definition = ontology.relations_by_id.get(inventory_id)
        if definition is None:
            raise ValueError(
                f"CIROH Hub relation rule {relation_name!r} uses unknown ontology inventory ID {inventory_id!r}"
            )
        actual_name = definition.get("name")
        if actual_name != relation_name:
            raise ValueError(
                f"CIROH Hub relation rule {relation_name!r} binds to {inventory_id!r}, "
                f"whose ontology name is {actual_name!r}"
            )


def load_ontology_registry(path: Path = DEFAULT_ONTOLOGY_SPEC) -> OntologyRegistry:
    """Load class/relation IDs and domains from the authoritative ontology YAML."""
    raw_bytes = path.read_bytes()
    document = yaml.safe_load(raw_bytes)
    if not isinstance(document, dict):
        raise ValueError("Ontology specification root must be an object")
    classes = document.get("classes")
    relations = document.get("relations")
    if not isinstance(classes, list) or not isinstance(relations, list):
        raise ValueError("Ontology specification must contain classes and relations arrays")
    class_map = {str(item["id"]): item for item in classes}
    relation_map = {str(item["id"]): item for item in relations}
    ontology = OntologyRegistry(
        classes_by_id=class_map,
        relations_by_id=relation_map,
        version=str((document.get("ontology") or {}).get("version") or ""),
        sha256=sha256_bytes(raw_bytes),
    )
    validate_hub_rule_bindings(ontology)
    return ontology


@dataclass(frozen=True)
class Node:
    """One deterministic Phase B node record."""

    id: str
    class_name: str
    inventory_id: str
    attributes: JsonObject
    canonical_key: str
    identity_regime: str
    curation_status: str
    evidence: JsonObject
    internal_lineage: JsonObject

    def to_dict(self) -> JsonObject:
        """Return the required stable node shape."""
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


@dataclass(frozen=True)
class Edge:
    """One deterministic Phase B edge record."""

    id: str
    relation: str
    inventory_id: str
    source: str
    target: str
    attributes: JsonObject
    evidence: JsonObject
    internal_lineage: JsonObject

    def to_dict(self) -> JsonObject:
        """Return the required stable edge shape."""
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
    """Accumulate graph and report records with deterministic conflict detection."""

    phase_a_version: str
    nodes: dict[str, Node] = field(default_factory=dict)
    edges: dict[str, Edge] = field(default_factory=dict)
    reports: dict[str, dict[str, JsonObject]] = field(
        default_factory=lambda: {"deferred": {}, "skipped": {}, "unresolved": {}, "warnings": {}}
    )

    def emit_node(self, node: Node) -> str:
        """Emit a node or reject conflicting content under the same ID."""
        existing = self.nodes.get(node.id)
        if existing is not None and existing != node:
            raise ValueError(f"Conflicting node content for deterministic ID {node.id}")
        self.nodes[node.id] = node
        return node.id

    def emit_edge(
        self,
        relation: str,
        source: str,
        target: str,
        attributes: JsonObject,
        evidence_text: Any,
        source_location: str,
        source_artifact: str,
        version: Any,
        lineage: JsonObject,
        qualifier: str = "",
    ) -> str:
        """Construct and emit one relation edge with deterministic evidence."""
        edge_id = make_edge_id(source, relation, target, qualifier)
        edge = Edge(
            id=edge_id,
            relation=relation,
            inventory_id=HUB_RELATION_RULE_IDS[relation],
            source=source,
            target=target,
            attributes=attributes,
            evidence=make_evidence(edge_id, evidence_text, source_location, source_artifact, version),
            internal_lineage=lineage,
        )
        existing = self.edges.get(edge_id)
        if existing is not None and existing != edge:
            raise ValueError(f"Conflicting edge content for deterministic ID {edge_id}")
        self.edges[edge_id] = edge
        return edge_id

    def record(
        self,
        report_type: str,
        page_url: str | None,
        page_path: str | None,
        source_path: str,
        source_ordinal: int | None,
        value: Any,
        reason: str,
    ) -> None:
        """Record one deterministic extraction disposition."""
        record: JsonObject = {
            "pageUrl": page_url,
            "pagePath": page_path,
            "category": report_type.removesuffix("s"),
            "sourcePath": source_path,
            "sourceOrdinal": source_ordinal,
            "value": value,
            "reason": reason,
        }
        self.reports[report_type][stable_json(record)] = record


@dataclass(frozen=True)
class PageContext:
    """Frequently reused identity and provenance values for one Hub page."""

    page: Mapping[str, Any]
    page_id: str
    page_type: str | None
    phase_a_version: str

    @property
    def url(self) -> str:
        """Return the canonical public page URL."""
        return str(self.page["canonical_url"])

    @property
    def version(self) -> str:
        """Return the materialized page-content hash."""
        return str(self.page["content_sha256"])

    def lineage(
        self,
        field_path: str,
        source_line: int | None = None,
        source_ordinal: int | None = None,
    ) -> JsonObject:
        """Build page-scoped internal lineage."""
        return make_lineage(self.phase_a_version, field_path, self.page, source_line, source_ordinal)


def _require_exact_keys(value: Any, expected: frozenset[str], context: str) -> Mapping[str, Any]:
    """Validate a fixed Phase A object shape and return it as a mapping."""
    if not isinstance(value, dict):
        raise ValueError(f"{context} must be an object")
    actual = set(value)
    if actual != expected:
        raise ValueError(f"{context} keys differ: missing={sorted(expected - actual)}, extra={sorted(actual - expected)}")
    return value


def validate_input_corpus(corpus: Mapping[str, Any]) -> None:
    """Fail fast when the Phase A corpus violates its supported fixed schema."""
    _require_exact_keys(corpus, TOP_LEVEL_FIELDS, "Phase A corpus")
    if corpus.get("schema_version") not in SUPPORTED_SOURCE_SCHEMAS:
        raise ValueError(f"Unsupported Phase A schema version {corpus.get('schema_version')!r}")
    if corpus.get("phase_a_version") not in SUPPORTED_PHASE_A_VERSIONS:
        raise ValueError(f"Unsupported Phase A implementation version {corpus.get('phase_a_version')!r}")
    source = _require_exact_keys(corpus.get("source"), SOURCE_FIELDS, "source")
    if source.get("artifact_type") != SOURCE_TYPE:
        raise ValueError(f"source.artifact_type must be {SOURCE_TYPE!r}")
    pages = corpus.get("pages")
    if not isinstance(pages, list):
        raise ValueError("pages must be an array")
    canonical_urls: set[str] = set()
    corpus_paths: set[str] = set()
    page_by_url: dict[str, Mapping[str, Any]] = {}
    for page_index, page_value in enumerate(pages):
        page = _require_exact_keys(page_value, PAGE_FIELDS, f"pages[{page_index}]")
        canonical_url = nonempty_text(page.get("canonical_url"))
        corpus_path = nonempty_text(page.get("corpus_path"))
        for key in ("page_key", "canonical_url", "title", "source_group", "corpus_path", "source_path", "content_sha256", "file_sha256"):
            if not nonempty_text(page.get(key)):
                raise ValueError(f"pages[{page_index}].{key} must be nonempty")
        if canonical_url in canonical_urls:
            raise ValueError(f"Duplicate page canonical URL: {canonical_url}")
        if corpus_path in corpus_paths:
            raise ValueError(f"Duplicate page corpus path: {corpus_path}")
        canonical_urls.add(canonical_url)
        corpus_paths.add(corpus_path)
        page_by_url[canonical_url] = page
        line_count = len(str(page.get("content_mdx") or "").splitlines())
        headings = page.get("headings")
        links = page.get("links")
        tags = page.get("tags")
        authors = page.get("authors")
        external_sources = page.get("external_content_sources")
        warnings = page.get("warnings")
        for field_name, values in (("headings", headings), ("links", links), ("tags", tags), ("authors", authors), ("external_content_sources", external_sources), ("warnings", warnings)):
            if not isinstance(values, list):
                raise ValueError(f"pages[{page_index}].{field_name} must be an array")
        heading_ordinals: set[int] = set()
        for heading_index, heading_value in enumerate(headings):
            heading = _require_exact_keys(heading_value, HEADING_FIELDS, f"pages[{page_index}].headings[{heading_index}]")
            ordinal = heading.get("ordinal")
            source_line = heading.get("source_line")
            if not isinstance(ordinal, int) or not isinstance(source_line, int) or not 1 <= source_line <= max(1, line_count):
                raise ValueError(f"Invalid heading ordinal/source line in page {canonical_url}")
            heading_ordinals.add(ordinal)
            parent = heading.get("parent_heading_ordinal")
            if parent is not None and (not isinstance(parent, int) or parent >= ordinal):
                raise ValueError(f"Invalid heading parent in page {canonical_url}: {parent!r}")
        if sorted(heading_ordinals) != list(range(1, len(headings) + 1)):
            raise ValueError(f"Heading ordinals are not contiguous in page {canonical_url}")
        link_ordinals: set[int] = set()
        for link_index, link_value in enumerate(links):
            link = _require_exact_keys(link_value, LINK_FIELDS, f"pages[{page_index}].links[{link_index}]")
            ordinal = link.get("ordinal")
            source_line = link.get("source_line")
            if not isinstance(ordinal, int) or not isinstance(source_line, int) or not 1 <= source_line <= max(1, line_count):
                raise ValueError(f"Invalid link ordinal/source line in page {canonical_url}")
            if link.get("heading_ordinal") is not None and link["heading_ordinal"] not in heading_ordinals:
                raise ValueError(f"Link references missing heading in page {canonical_url}")
            link_ordinals.add(ordinal)
        if sorted(link_ordinals) != list(range(1, len(links) + 1)):
            raise ValueError(f"Link ordinals are not contiguous in page {canonical_url}")
        for author_index, author in enumerate(authors):
            _require_exact_keys(author, AUTHOR_FIELDS, f"pages[{page_index}].authors[{author_index}]")
        for source_index, external in enumerate(external_sources):
            _require_exact_keys(external, EXTERNAL_SOURCE_FIELDS, f"pages[{page_index}].external_content_sources[{source_index}]")
        for warning_index, warning in enumerate(warnings):
            _require_exact_keys(warning, WARNING_FIELDS, f"pages[{page_index}].warnings[{warning_index}]")
    for page in pages:
        parent_url = page.get("parent_url")
        if parent_url is not None and parent_url not in page_by_url:
            raise ValueError(f"Missing parent_url target {parent_url!r} for {page['canonical_url']}")
    for index, exclusion in enumerate(corpus.get("known_exclusions") or []):
        _require_exact_keys(exclusion, KNOWN_EXCLUSION_FIELDS, f"known_exclusions[{index}]")
    for index, warning in enumerate(corpus.get("warnings") or []):
        _require_exact_keys(warning, WARNING_FIELDS, f"warnings[{index}]")
    summary = _require_exact_keys(corpus.get("summary"), SUMMARY_FIELDS, "summary")
    expected_summary = {
        "total_pages": len(pages),
        "total_headings": sum(len(page["headings"]) for page in pages),
        "total_links": sum(len(page["links"]) for page in pages),
        "total_external_content_sources": sum(len(page["external_content_sources"]) for page in pages),
        "generated_from_js": sum(bool(page["generated_from_js"]) for page in pages),
        "page_warning_count": sum(len(page["warnings"]) for page in pages),
        "top_level_warning_count": len(corpus.get("warnings") or []),
    }
    for key, expected in expected_summary.items():
        if summary.get(key) != expected:
            raise ValueError(f"summary.{key}={summary.get(key)!r}, expected {expected}")


def load_corpus(path: Path) -> tuple[JsonObject, str]:
    """Load the supported Phase A corpus and return its exact byte hash."""
    raw_bytes = path.read_bytes()
    try:
        corpus = json.loads(raw_bytes)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Unable to parse Phase A corpus {path}: {exc}") from exc
    if not isinstance(corpus, dict):
        raise ValueError("Phase A corpus root must be an object")
    validate_input_corpus(corpus)
    return corpus, sha256_bytes(raw_bytes)


def _node(
    node_id: str,
    class_name: str,
    attributes: JsonObject,
    canonical_key: str,
    identity_regime: str,
    curation_status: str,
    evidence_text: Any,
    source_location: str,
    source_artifact: str,
    version: Any,
    lineage: JsonObject,
) -> Node:
    """Construct a complete node with its formal inventory ID and evidence."""
    return Node(
        id=node_id,
        class_name=class_name,
        inventory_id=HUB_NODE_RULE_IDS[class_name],
        attributes=attributes,
        canonical_key=canonical_key,
        identity_regime=identity_regime,
        curation_status=curation_status,
        evidence=make_evidence(node_id, evidence_text, source_location, source_artifact, version),
        internal_lineage=lineage,
    )


def _page_attributes(page: Mapping[str, Any], page_type: str | None) -> JsonObject:
    """Project the complete deterministic page attributes from Phase A."""
    return {
        "canonicalUrl": page["canonical_url"],
        "path": page["path"],
        "slug": page["slug"],
        "title": page["title"],
        "titleSource": page["title_source"],
        "description": page["description"],
        "lastUpdatedDate": page["last_updated_date"],
        "lastUpdatedDateRaw": page["last_updated_date_raw"],
        "sourceGroup": page["source_group"],
        "pageType": page_type,
        "corpusPath": page["corpus_path"],
        "sourcePath": page["source_path"],
        "generatedFromJs": bool(page["generated_from_js"]),
        "fileSha256": page["file_sha256"],
        "contentSha256": page["content_sha256"],
        "headingCount": len(page["headings"]),
        "linkCount": len(page["links"]),
        "externalContentSourceCount": len(page["external_content_sources"]),
        "tagCount": len(page["tags"]),
        "authorCount": len(page["authors"]),
    }


def _author_evidence_text(author: Mapping[str, Any]) -> str:
    """Build exact author evidence text from materialized fields."""
    text = str(author.get("name") or "").strip()
    if author.get("role"):
        text += f"; role: {str(author['role']).strip()}"
    if author.get("affiliation"):
        text += f"; affiliation: {str(author['affiliation']).strip()}"
    return text


def _person_identity(author: Mapping[str, Any]) -> tuple[str, str]:
    """Select the best permitted deterministic agent alignment candidate."""
    profile_url = str(author.get("url") or "").strip()
    orcid_match = ORCID_RE.search(profile_url)
    if orcid_match:
        return f"orcid:{orcid_match.group(1).upper()}", "orcid"
    github_login = github_login_from_profile(profile_url)
    if github_login:
        return f"github-login:{github_login.casefold()}", "github_login"
    normalized_name = normalize_text_key(str(author.get("name") or ""))
    normalized_affiliation = normalize_text_key(str(author.get("affiliation") or ""))
    if normalized_affiliation:
        return f"person-name-affiliation:{normalized_name}|{normalized_affiliation}", "normalized_name_affiliation"
    return f"person-name:{normalized_name}", "normalized_name"


def _repository_declaration(
    context: PageContext,
    source_path: str,
    source_ordinal: int,
    source_line: int,
    raw_target: str,
    source_kind: str,
    evidence_text: str,
    path: str | None = None,
) -> JsonObject:
    """Build a stable exact-target declaration for semantic aggregation."""
    return {
        "pageUrl": context.url,
        "pagePath": context.page["corpus_path"],
        "sourcePath": source_path,
        "sourceOrdinal": source_ordinal,
        "sourceLine": source_line,
        "rawTarget": raw_target,
        "sourceKind": source_kind,
        "evidenceText": evidence_text,
        "version": context.version,
        "path": path,
    }


def _emit_page_local_nodes(
    context: PageContext,
    builder: GraphBuilder,
    subject_declarations: dict[str, list[JsonObject]],
) -> None:
    """Emit a page, URL identifier, structure, tags, and agent mentions."""
    page = context.page
    page_id = context.page_id
    builder.emit_node(
        _node(
            page_id,
            "DocumentationPage",
            _page_attributes(page, context.page_type),
            f"hub-page-url:{context.url}",
            "canonical_page_url",
            CURATED,
            page["title"],
            context.url,
            context.url,
            context.version,
            context.lineage(f"pages[canonical_url={context.url}]"),
        )
    )
    identifier_id = make_exact_identifier_id("page_url", context.url)
    builder.emit_node(
        _node(
            identifier_id,
            "Identifier",
            {"idType": "page_url", "value": context.url, "normalizedValue": context.url},
            f"url:{context.url}",
            "exact_url",
            CURATED,
            context.url,
            context.url,
            context.url,
            context.version,
            context.lineage("canonical_url"),
        )
    )
    builder.emit_edge(
        "hasIdentifier",
        page_id,
        identifier_id,
        {},
        context.url,
        context.url,
        context.url,
        context.version,
        context.lineage("canonical_url"),
    )
    heading_ids = {int(item["ordinal"]): make_section_id(context.url, int(item["ordinal"])) for item in page["headings"]}
    for heading in page["headings"]:
        ordinal = int(heading["ordinal"])
        section_id = heading_ids[ordinal]
        parent_ordinal = heading["parent_heading_ordinal"]
        builder.emit_node(
            _node(
                section_id,
                "Section",
                {
                    "pageUrl": context.url,
                    "ordinal": ordinal,
                    "level": heading["level"],
                    "text": heading["text"],
                    "rawText": heading["raw_text"],
                    "sourceLine": heading["source_line"],
                    "parentHeadingOrdinal": parent_ordinal,
                    "parentSectionId": heading_ids.get(parent_ordinal),
                },
                f"hub-section:{context.url}:heading:{ordinal}",
                "page_heading_ordinal",
                CURATED,
                heading["raw_text"],
                context.url,
                context.url,
                context.version,
                context.lineage(f"headings[ordinal={ordinal}]", int(heading["source_line"]), ordinal),
            )
        )
        builder.emit_edge(
            "hasSection",
            page_id,
            section_id,
            {},
            heading["raw_text"],
            context.url,
            context.url,
            context.version,
            context.lineage(f"headings[ordinal={ordinal}]", int(heading["source_line"]), ordinal),
        )
    for link in page["links"]:
        ordinal = int(link["ordinal"])
        link_id = make_link_id(context.url, ordinal)
        heading_ordinal = link["heading_ordinal"]
        evidence_text = (
            f"{link['anchor_text']} → {link['raw_target']}" if link["anchor_text"] else link["raw_target"]
        )
        builder.emit_node(
            _node(
                link_id,
                "Link",
                {
                    "pageUrl": context.url,
                    "ordinal": ordinal,
                    "anchorText": link["anchor_text"],
                    "rawTarget": link["raw_target"],
                    "resolvedUrl": link["resolved_url"],
                    "linkType": link["link_type"],
                    "sourceLine": link["source_line"],
                    "headingOrdinal": heading_ordinal,
                    "sectionId": heading_ids.get(heading_ordinal),
                },
                f"hub-link-occurrence:{context.url}:{ordinal}",
                "page_link_ordinal",
                CURATED,
                evidence_text,
                context.url,
                context.url,
                context.version,
                context.lineage(f"links[ordinal={ordinal}]", int(link["source_line"]), ordinal),
            )
        )
        builder.emit_edge(
            "linksTo",
            page_id,
            link_id,
            {},
            evidence_text,
            context.url,
            context.url,
            context.version,
            context.lineage(f"links[ordinal={ordinal}]", int(link["source_line"]), ordinal),
        )
    for tag_index, tag_value in enumerate(page["tags"], start=1):
        tag = str(tag_value)
        normalized_tag = normalize_text_key(tag)
        if not normalized_tag:
            builder.record("skipped", context.url, str(page["corpus_path"]), f"tags[{tag_index - 1}]", tag_index, tag, "empty_subject_label")
            continue
        subject_id = f"hub:subject:{stable_hash(normalized_tag)}"
        declaration = {
            "pageUrl": context.url,
            "pagePath": page["corpus_path"],
            "sourcePath": f"tags[{tag_index - 1}]",
            "sourceOrdinal": tag_index,
            "sourceLine": None,
            "rawTarget": tag,
            "sourceLabel": tag,
            "version": context.version,
        }
        subject_declarations[normalized_tag].append(declaration)
        builder.emit_edge(
            "hasSubject",
            page_id,
            subject_id,
            {"sourceLabel": tag, "ordinal": tag_index},
            tag,
            context.url,
            context.url,
            context.version,
            context.lineage(f"tags[{tag_index - 1}]", source_ordinal=tag_index),
            qualifier=f"tag:{tag_index}",
        )
    for author_index, author in enumerate(page["authors"], start=1):
        name = str(author.get("name") or "").strip()
        if not name:
            builder.record(
                "deferred",
                context.url,
                str(page["corpus_path"]),
                f"authors[{author_index - 1}]",
                author_index,
                author,
                "author_identifier_without_materialized_identity",
            )
            continue
        person_id = f"hub:person:{stable_hash(context.url)}:{author_index:03d}"
        canonical_key, identity_regime = _person_identity(author)
        normalized_name = normalize_text_key(name)
        normalized_affiliation = normalize_text_key(str(author.get("affiliation") or ""))
        evidence_text = _author_evidence_text(author)
        builder.emit_node(
            _node(
                person_id,
                "Person",
                {
                    "name": name,
                    "normalizedName": normalized_name,
                    "role": author.get("role"),
                    "affiliation": author.get("affiliation"),
                    "profileUrl": author.get("url"),
                    "source": author.get("source"),
                    "sourceIdentifier": None,
                    "authorOrdinal": author_index,
                    "alignmentCandidateKey": canonical_key,
                },
                canonical_key,
                identity_regime,
                CURATED,
                evidence_text,
                context.url,
                context.url,
                context.version,
                context.lineage(f"authors[{author_index - 1}]", source_ordinal=author_index),
            )
        )
        builder.emit_edge(
            "hasContributor",
            page_id,
            person_id,
            {"role": "author", "sourceRole": author.get("role"), "ordinal": author_index},
            evidence_text,
            context.url,
            context.url,
            context.version,
            context.lineage(f"authors[{author_index - 1}]", source_ordinal=author_index),
        )
        affiliation = str(author.get("affiliation") or "").strip()
        if affiliation:
            organization_id = f"hub:organization:{stable_hash(context.url)}:{author_index:03d}"
            organization_key = f"organization-name:{normalized_affiliation}"
            builder.emit_node(
                _node(
                    organization_id,
                    "Organization",
                    {
                        "name": affiliation,
                        "normalizedName": normalized_affiliation,
                        "authorOrdinal": author_index,
                        "alignmentCandidateKey": organization_key,
                    },
                    organization_key,
                    "exact_normalized_name_candidate",
                    CURATED,
                    affiliation,
                    context.url,
                    context.url,
                    context.version,
                    context.lineage(f"authors[{author_index - 1}].affiliation", source_ordinal=author_index),
                )
            )
            builder.emit_edge(
                "affiliatedWith",
                person_id,
                organization_id,
                {},
                affiliation,
                context.url,
                context.url,
                context.version,
                context.lineage(f"authors[{author_index - 1}].affiliation", source_ordinal=author_index),
            )


def _emit_subject_nodes(
    declarations_by_key: Mapping[str, Sequence[Mapping[str, Any]]],
    contexts_by_url: Mapping[str, PageContext],
    builder: GraphBuilder,
) -> None:
    """Emit exact-normalization Subject nodes after collecting all source labels."""
    for normalized_tag in sorted(declarations_by_key):
        declarations = declarations_by_key[normalized_tag]
        primary, ordered = select_primary_declaration(declarations)
        label_counts = Counter(str(item["sourceLabel"]) for item in declarations)
        preferred_label = min(label_counts, key=lambda value: (-label_counts[value], value))
        context = contexts_by_url[str(primary["pageUrl"])]
        subject_id = f"hub:subject:{stable_hash(normalized_tag)}"
        builder.emit_node(
            _node(
                subject_id,
                "Subject",
                {
                    "preferredLabel": preferred_label,
                    "normalizedLabel": normalized_tag,
                    "sourceLabels": sorted(label_counts),
                    "sourceDeclarations": ordered,
                },
                f"subject-label:{normalized_tag}",
                "exact_normalized_label",
                CURATED,
                primary["sourceLabel"],
                context.url,
                context.url,
                context.version,
                context.lineage(str(primary["sourcePath"]), source_ordinal=int(primary["sourceOrdinal"])),
            )
        )


def _emit_source_repository_and_files(
    pages: Sequence[Mapping[str, Any]],
    contexts_by_url: Mapping[str, PageContext],
    repository_url: str,
    repository_ref: str,
    builder: GraphBuilder,
) -> tuple[str, dict[str, str]]:
    """Emit the configured source repository, its identifier, and distinct source files."""
    repository_id = f"hub:repository:{stable_hash(repository_url)}"
    owner, repository_name = urlsplit(repository_url).path.strip("/").split("/", 1)
    builder.emit_node(
        _node(
            repository_id,
            "Repository",
            {
                "htmlUrl": repository_url,
                "owner": owner,
                "name": repository_name,
                "repositoryRef": repository_ref,
                "role": "ciroh_hub_source_repository",
            },
            f"github-repo-url:{repository_url.casefold()}",
            "github_repository_url",
            REFERENCED,
            repository_url,
            repository_url,
            repository_url,
            repository_ref,
            make_lineage(builder.phase_a_version, "source_repository_configuration"),
        )
    )
    identifier_id = make_exact_identifier_id("github_repo_url", repository_url)
    builder.emit_node(
        _node(
            identifier_id,
            "Identifier",
            {"idType": "github_repository_url", "value": repository_url, "normalizedValue": repository_url},
            f"github-repo-url:{repository_url.casefold()}",
            "exact_url",
            REFERENCED,
            repository_url,
            repository_url,
            repository_url,
            repository_ref,
            make_lineage(builder.phase_a_version, "source_repository_configuration.url"),
        )
    )
    builder.emit_edge(
        "hasIdentifier",
        repository_id,
        identifier_id,
        {},
        repository_url,
        repository_url,
        repository_url,
        repository_ref,
        make_lineage(builder.phase_a_version, "source_repository_configuration.url"),
    )
    declarations_by_path: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for page in pages:
        declarations_by_path[str(page["source_path"])].append(page)
    file_ids: dict[str, str] = {}
    for source_path in sorted(declarations_by_path):
        page_declarations = sorted(declarations_by_path[source_path], key=lambda item: str(item["canonical_url"]))
        primary_page = page_declarations[0]
        generated_flags = {bool(item["generated_from_js"]) for item in page_declarations}
        if len(generated_flags) != 1:
            raise ValueError(f"Shared source path has conflicting generated_from_js values: {source_path}")
        generated = generated_flags.pop()
        if not generated and len({str(item["file_sha256"]) for item in page_declarations}) != 1:
            raise ValueError(f"Shared direct source path has conflicting file hashes: {source_path}")
        context = contexts_by_url[str(primary_page["canonical_url"])]
        file_id = make_source_file_id(repository_url, source_path)
        file_ids[source_path] = file_id
        source_url = build_source_blob_url(repository_url, repository_ref, source_path)
        suffix = PurePosixPath(source_path).suffix
        if generated:
            evidence_text = f"{source_path} materialized as {primary_page['corpus_path']}"
            version = f"materialized:{primary_page['content_sha256']}"
            attributes = {
                "path": source_path,
                "fileName": PurePosixPath(source_path).name,
                "extension": suffix,
                "fileRole": "hub_page_source",
                "selectionReason": "public_hub_page_source",
                "sourceRepositoryUrl": repository_url,
                "sourceRepositoryRef": repository_ref,
                "sourceUrl": source_url,
                "generatedFromJs": True,
                "downloaded": False,
                "contentAvailable": False,
                "sourceHashAvailable": False,
                "fileSha256": None,
                "materializedCorpusPath": primary_page["corpus_path"],
                "materializedFileSha256": primary_page["file_sha256"],
                "materializedContentSha256": primary_page["content_sha256"],
            }
        else:
            evidence_text = source_path
            version = primary_page["file_sha256"]
            attributes = {
                "path": source_path,
                "fileName": PurePosixPath(source_path).name,
                "extension": suffix,
                "fileRole": "hub_page_source",
                "selectionReason": "public_hub_page_source",
                "sourceRepositoryUrl": repository_url,
                "sourceRepositoryRef": repository_ref,
                "sourceUrl": source_url,
                "generatedFromJs": False,
                "downloaded": True,
                "contentAvailable": True,
                "sourceHashAvailable": True,
                "fileSha256": primary_page["file_sha256"],
                "materializedCorpusPath": None,
                "materializedFileSha256": None,
                "materializedContentSha256": None,
            }
        if len(page_declarations) > 1:
            attributes["sourceDeclarations"] = [
                {"pageUrl": item["canonical_url"], "corpusPath": item["corpus_path"], "sourcePath": source_path}
                for item in page_declarations
            ]
        builder.emit_node(
            _node(
                file_id,
                "RepoFile",
                attributes,
                f"github-file-path:{repository_url.casefold()}:{source_path}",
                "repository_relative_path",
                CURATED,
                evidence_text,
                source_url,
                repository_url,
                version,
                context.lineage("source_path"),
            )
        )
        builder.emit_edge(
            "hasFile",
            repository_id,
            file_id,
            {},
            evidence_text,
            source_url,
            repository_url,
            version,
            context.lineage("source_path"),
        )
        for page in page_declarations:
            page_context = contexts_by_url[str(page["canonical_url"])]
            builder.emit_edge(
                "hasSourceFile",
                page_context.page_id,
                file_id,
                {
                    "generatedFromJs": bool(page["generated_from_js"]),
                    "corpusPath": page["corpus_path"],
                    "sourcePath": source_path,
                },
                evidence_text,
                source_url,
                repository_url,
                version,
                page_context.lineage("source_path"),
            )
    return repository_id, file_ids


def _product_card_headings(page: Mapping[str, Any], page_type: str | None) -> list[Mapping[str, Any]]:
    """Detect catalog card headings mechanically from repeated direct-child structure."""
    if page_type != "product-catalog":
        return []
    by_parent: dict[int, list[Mapping[str, Any]]] = defaultdict(list)
    for heading in page["headings"]:
        parent = heading.get("parent_heading_ordinal")
        if isinstance(parent, int):
            by_parent[parent].append(heading)
    candidates = [(len(children), parent, children) for parent, children in by_parent.items() if len(children) >= 2]
    if not candidates:
        return []
    _, _, children = max(candidates, key=lambda item: (item[0], -item[1]))
    return sorted(children, key=lambda item: int(item["ordinal"]))


def _emit_hierarchy(contexts: Sequence[PageContext], contexts_by_url: Mapping[str, PageContext], builder: GraphBuilder) -> None:
    """Emit the exact parent hierarchy and its declared inverse."""
    for context in contexts:
        parent_url = context.page.get("parent_url")
        if parent_url is None:
            continue
        parent = contexts_by_url[str(parent_url)]
        evidence_text = f"{context.url} is part of {parent.url}"
        builder.emit_edge(
            "isPartOf",
            context.page_id,
            parent.page_id,
            {},
            evidence_text,
            context.url,
            context.url,
            context.version,
            context.lineage("parent_url"),
        )
        builder.emit_edge(
            "hasSubPage",
            parent.page_id,
            context.page_id,
            {},
            evidence_text,
            context.url,
            context.url,
            context.version,
            context.lineage("parent_url"),
        )


def _semantic_edge_attributes(declarations: Sequence[Mapping[str, Any]], **extra: Any) -> JsonObject:
    """Build semantic-edge attributes retaining every exact source declaration."""
    _, ordered = select_primary_declaration(declarations)
    result = {key: value for key, value in extra.items()}
    result["sourceDeclarations"] = ordered
    return result


def _lineage_from_declaration(phase_a_version: str, declaration: Mapping[str, Any], page: Mapping[str, Any]) -> JsonObject:
    """Build precise lineage for the primary exact-target declaration."""
    return make_lineage(
        phase_a_version,
        str(declaration["sourcePath"]),
        page,
        declaration.get("sourceLine") if isinstance(declaration.get("sourceLine"), int) else None,
        declaration.get("sourceOrdinal") if isinstance(declaration.get("sourceOrdinal"), int) else None,
    )


def _emit_exact_targets_and_relations(
    contexts: Sequence[PageContext],
    contexts_by_url: Mapping[str, PageContext],
    page_aliases: Mapping[str, str],
    known_excluded_routes: set[str],
    source_repository_url: str,
    source_repository_id: str,
    builder: GraphBuilder,
) -> None:
    """Resolve exact links/components and emit only mapping-authorized semantic relations."""
    repository_declarations: dict[str, list[JsonObject]] = defaultdict(list)
    repository_reference_edges: dict[tuple[str, str], list[JsonObject]] = defaultdict(list)
    documents_edges: dict[tuple[str, str, str], list[JsonObject]] = defaultdict(list)
    repository_announcement_edges: dict[tuple[str, str], list[JsonObject]] = defaultdict(list)
    dataset_declarations: dict[str, list[JsonObject]] = defaultdict(list)
    dataset_reference_edges: dict[tuple[str, str], list[JsonObject]] = defaultdict(list)
    page_reference_declarations: dict[str, list[JsonObject]] = defaultdict(list)
    page_announcement_edges: dict[tuple[str, str], list[JsonObject]] = defaultdict(list)

    for context in contexts:
        page = context.page
        if context.page_type is None:
            builder.record("deferred", context.url, str(page["corpus_path"]), "pageType", None, None, "page_type_not_deterministically_classified")
        for heading in _product_card_headings(page, context.page_type):
            builder.record(
                "deferred",
                context.url,
                str(page["corpus_path"]),
                f"headings[ordinal={heading['ordinal']}]",
                int(heading["ordinal"]),
                heading["text"],
                "product_card_semantic_typing_deferred",
            )
        for link in page["links"]:
            ordinal = int(link["ordinal"])
            source_path = f"links[ordinal={ordinal}]"
            raw_target = str(link["raw_target"])
            resolved = link.get("resolved_url")
            evidence_text = f"{link['anchor_text']} → {raw_target}" if link.get("anchor_text") else raw_target
            declaration = _repository_declaration(
                context,
                source_path,
                ordinal,
                int(link["source_line"]),
                raw_target,
                "link",
                evidence_text,
            )
            github_root = normalize_github_repo_url(str(resolved or raw_target)) if link["link_type"] == "github" else None
            if link["link_type"] == "github":
                if github_root:
                    repository_declarations[github_root.casefold()].append(declaration)
                    repository_reference_edges[(context.page_id, github_root.casefold())].append(declaration)
                    pull_request = parse_github_pull_request(str(resolved or raw_target))
                    if context.page_type in {"release-note", "blog-post"} and pull_request:
                        repository_announcement_edges[(context.page_id, github_root.casefold())].append(declaration)
                else:
                    builder.record("unresolved", context.url, str(page["corpus_path"]), source_path, ordinal, raw_target, "github_repository_target_unparseable")
            resource_id = extract_hydroshare_resource_id(str(resolved or raw_target))
            if resource_id:
                dataset_declarations[resource_id].append(declaration)
                dataset_reference_edges[(context.page_id, resource_id)].append(declaration)
            elif link["link_type"] == "hydroshare":
                builder.record("unresolved", context.url, str(page["corpus_path"]), source_path, ordinal, raw_target, "invalid_hydroshare_resource_url")
            if link["link_type"] == "doi":
                builder.record("deferred", context.url, str(page["corpus_path"]), source_path, ordinal, normalize_doi(str(resolved or raw_target)) or raw_target, "doi_target_type_requires_context")
            elif link["link_type"] == "other_absolute":
                builder.record("deferred", context.url, str(page["corpus_path"]), source_path, ordinal, raw_target, "other_absolute_link_semantics_unknown")
            if link["link_type"] == "relative" and resolved is None:
                builder.record("unresolved", context.url, str(page["corpus_path"]), source_path, ordinal, raw_target, "relative_link_without_resolved_url")
            if context.page_type == "release-note" and link["link_type"] in {"hub_internal", "relative"} and resolved:
                normalized_target = normalize_hub_url(str(resolved))
                if not normalized_target:
                    builder.record("unresolved", context.url, str(page["corpus_path"]), source_path, ordinal, raw_target, "hub_internal_target_unparseable")
                    continue
                target_url = page_aliases.get(normalized_target)
                if target_url == context.url:
                    continue
                if target_url:
                    page_announcement_edges[(context.page_id, target_url)].append(declaration)
                elif normalized_target in known_excluded_routes:
                    builder.record("skipped", context.url, str(page["corpus_path"]), source_path, ordinal, normalized_target, "known_excluded_route_delegated")
                else:
                    page_reference_declarations[normalized_target].append(declaration)
                    page_announcement_edges[(context.page_id, normalized_target)].append(declaration)
        for external in page["external_content_sources"]:
            ordinal = int(external["ordinal"])
            source_path = f"external_content_sources[ordinal={ordinal}]"
            username = str(external.get("username") or "").strip()
            repository = str(external.get("repository") or "").strip()
            candidate = f"https://github.com/{username}/{repository}" if username and repository else ""
            github_root = normalize_github_repo_url(candidate)
            evidence_text = f"{external['component']} {username}/{repository}:{external['path']}"
            declaration = _repository_declaration(
                context,
                source_path,
                ordinal,
                int(external["source_line"]),
                candidate,
                str(external["component"]),
                evidence_text,
                str(external["path"]),
            )
            if not github_root:
                builder.record("unresolved", context.url, str(page["corpus_path"]), source_path, ordinal, external, "external_component_missing_repository_identity")
                continue
            key = github_root.casefold()
            repository_declarations[key].append(declaration)
            repository_reference_edges[(context.page_id, key)].append(declaration)
            if external["component"] == "GitHubReadme":
                documents_edges[(context.page_id, key, str(external["path"]))].append(declaration)
            elif external["component"] == "GitHubWikiPage":
                builder.record("deferred", context.url, str(page["corpus_path"]), source_path, ordinal, external["path"], "github_wiki_mirror_relation_not_declared")

    repository_ids: dict[str, str] = {source_repository_url.casefold(): source_repository_id}
    for repository_key in sorted(repository_declarations):
        declarations = repository_declarations[repository_key]
        primary, ordered = select_primary_declaration(declarations)
        normalized_url = normalize_github_repo_url(str(primary["rawTarget"]))
        if normalized_url is None:
            raise ValueError(f"Internal repository declaration lost exact URL: {primary!r}")
        if repository_key == source_repository_url.casefold():
            repository_ids[repository_key] = source_repository_id
            continue
        repository_id = f"hub:repository:{stable_hash(normalized_url)}"
        repository_ids[repository_key] = repository_id
        owner, name = urlsplit(normalized_url).path.strip("/").split("/", 1)
        context = contexts_by_url[str(primary["pageUrl"])]
        builder.emit_node(
            _node(
                repository_id,
                "Repository",
                {
                    "htmlUrl": normalized_url,
                    "owner": owner,
                    "name": name,
                    "originalTargets": sorted_unique(item["rawTarget"] for item in ordered),
                    "sourceKinds": sorted_unique(item["sourceKind"] for item in ordered),
                },
                f"github-repo-url:{normalized_url.casefold()}",
                "github_repository_url",
                REFERENCED,
                primary["evidenceText"],
                context.url,
                context.url,
                context.version,
                _lineage_from_declaration(builder.phase_a_version, primary, context.page),
            )
        )
        identifier_id = make_exact_identifier_id("github_repo_url", normalized_url)
        builder.emit_node(
            _node(
                identifier_id,
                "Identifier",
                {"idType": "github_repository_url", "value": normalized_url, "normalizedValue": normalized_url},
                f"github-repo-url:{normalized_url.casefold()}",
                "exact_identifier",
                REFERENCED,
                primary["evidenceText"],
                context.url,
                context.url,
                context.version,
                _lineage_from_declaration(builder.phase_a_version, primary, context.page),
            )
        )
        builder.emit_edge(
            "hasIdentifier",
            repository_id,
            identifier_id,
            {"sourceDeclarations": ordered},
            primary["evidenceText"],
            context.url,
            context.url,
            context.version,
            _lineage_from_declaration(builder.phase_a_version, primary, context.page),
        )
    for (page_id, repository_key), declarations in sorted(repository_reference_edges.items()):
        primary, _ = select_primary_declaration(declarations)
        context = contexts_by_url[str(primary["pageUrl"])]
        builder.emit_edge(
            "referencesRepository",
            page_id,
            repository_ids[repository_key],
            _semantic_edge_attributes(declarations),
            primary["evidenceText"],
            context.url,
            context.url,
            context.version,
            _lineage_from_declaration(builder.phase_a_version, primary, context.page),
        )
    for (page_id, repository_key, repository_path), declarations in sorted(documents_edges.items()):
        primary, _ = select_primary_declaration(declarations)
        context = contexts_by_url[str(primary["pageUrl"])]
        builder.emit_edge(
            "documents",
            page_id,
            repository_ids[repository_key],
            _semantic_edge_attributes(
                declarations,
                component="GitHubReadme",
                username=urlsplit(normalize_github_repo_url(str(primary["rawTarget"])) or "").path.strip("/").split("/")[0],
                repository=urlsplit(normalize_github_repo_url(str(primary["rawTarget"])) or "").path.strip("/").split("/")[1],
                repositoryPath=repository_path,
                componentOrdinal=primary["sourceOrdinal"],
                sourceLine=primary["sourceLine"],
                mirrorKind="materialized_repository_file",
            ),
            primary["evidenceText"],
            context.url,
            context.url,
            context.version,
            _lineage_from_declaration(builder.phase_a_version, primary, context.page),
            qualifier=repository_path,
        )
    for (page_id, repository_key), declarations in sorted(repository_announcement_edges.items()):
        primary, _ = select_primary_declaration(declarations)
        context = contexts_by_url[str(primary["pageUrl"])]
        pull_request = parse_github_pull_request(str(primary["rawTarget"]))
        if pull_request is None:
            raise ValueError("Announcement declaration lost pull-request identity")
        builder.emit_edge(
            "announces",
            page_id,
            repository_ids[repository_key],
            _semantic_edge_attributes(
                declarations,
                announcementTargetType="pull_request",
                pullRequestNumber=pull_request[1],
                targetUrl=primary["rawTarget"],
                pageType=context.page_type,
            ),
            primary["evidenceText"],
            context.url,
            context.url,
            context.version,
            _lineage_from_declaration(builder.phase_a_version, primary, context.page),
        )

    dataset_ids: dict[str, str] = {}
    for resource_id in sorted(dataset_declarations):
        declarations = dataset_declarations[resource_id]
        primary, ordered = select_primary_declaration(declarations)
        context = contexts_by_url[str(primary["pageUrl"])]
        dataset_id = f"hub:dataset:hydroshare:{resource_id}"
        dataset_ids[resource_id] = dataset_id
        resource_url = f"https://www.hydroshare.org/resource/{resource_id}/"
        builder.emit_node(
            _node(
                dataset_id,
                "DatasetResource",
                {"resourceId": resource_id, "resourceUrl": resource_url, "originalTargets": sorted_unique(item["rawTarget"] for item in ordered)},
                f"hydroshare-resource-id:{resource_id}",
                "hydroshare_resource_id",
                REFERENCED,
                primary["evidenceText"],
                context.url,
                context.url,
                context.version,
                _lineage_from_declaration(builder.phase_a_version, primary, context.page),
            )
        )
        identifier_id = make_exact_identifier_id("hydroshare_resource_id", resource_id)
        builder.emit_node(
            _node(
                identifier_id,
                "Identifier",
                {"idType": "hydroshare_resource_id", "value": resource_id, "normalizedValue": resource_id},
                f"hydroshare-resource-id:{resource_id}",
                "exact_identifier",
                REFERENCED,
                primary["evidenceText"],
                context.url,
                context.url,
                context.version,
                _lineage_from_declaration(builder.phase_a_version, primary, context.page),
            )
        )
        builder.emit_edge(
            "hasIdentifier",
            dataset_id,
            identifier_id,
            {"sourceDeclarations": ordered},
            primary["evidenceText"],
            context.url,
            context.url,
            context.version,
            _lineage_from_declaration(builder.phase_a_version, primary, context.page),
        )
    for (page_id, resource_id), declarations in sorted(dataset_reference_edges.items()):
        primary, _ = select_primary_declaration(declarations)
        context = contexts_by_url[str(primary["pageUrl"])]
        builder.emit_edge(
            "referencesDataset",
            page_id,
            dataset_ids[resource_id],
            _semantic_edge_attributes(declarations),
            primary["evidenceText"],
            context.url,
            context.url,
            context.version,
            _lineage_from_declaration(builder.phase_a_version, primary, context.page),
        )

    referenced_page_ids: dict[str, str] = {}
    for target_url in sorted(page_reference_declarations):
        declarations = page_reference_declarations[target_url]
        primary, ordered = select_primary_declaration(declarations)
        context = contexts_by_url[str(primary["pageUrl"])]
        page_id = f"hub:page-ref:{stable_hash(target_url)}"
        referenced_page_ids[target_url] = page_id
        builder.emit_node(
            _node(
                page_id,
                "DocumentationPage",
                {"canonicalUrl": target_url, "pageType": None, "title": None, "sourceGroup": None},
                f"hub-page-url:{target_url}",
                "canonical_page_url",
                REFERENCED,
                primary["evidenceText"],
                context.url,
                context.url,
                context.version,
                _lineage_from_declaration(builder.phase_a_version, primary, context.page),
            )
        )
        identifier_id = make_exact_identifier_id("page_url", target_url)
        builder.emit_node(
            _node(
                identifier_id,
                "Identifier",
                {"idType": "page_url", "value": target_url, "normalizedValue": target_url},
                f"url:{target_url}",
                "exact_identifier",
                REFERENCED,
                primary["evidenceText"],
                context.url,
                context.url,
                context.version,
                _lineage_from_declaration(builder.phase_a_version, primary, context.page),
            )
        )
        builder.emit_edge(
            "hasIdentifier",
            page_id,
            identifier_id,
            {"sourceDeclarations": ordered},
            primary["evidenceText"],
            context.url,
            context.url,
            context.version,
            _lineage_from_declaration(builder.phase_a_version, primary, context.page),
        )
    for (source_page_id, target_url), declarations in sorted(page_announcement_edges.items()):
        primary, _ = select_primary_declaration(declarations)
        context = contexts_by_url[str(primary["pageUrl"])]
        target_id = contexts_by_url[target_url].page_id if target_url in contexts_by_url else referenced_page_ids[target_url]
        builder.emit_edge(
            "announces",
            source_page_id,
            target_id,
            _semantic_edge_attributes(declarations, announcementTargetType="documentation_page", targetUrl=target_url),
            primary["evidenceText"],
            context.url,
            context.url,
            context.version,
            _lineage_from_declaration(builder.phase_a_version, primary, context.page),
        )


def _propagate_reports(corpus: Mapping[str, Any], contexts_by_url: Mapping[str, PageContext], builder: GraphBuilder) -> None:
    """Propagate Phase A warnings and known methodological exclusions."""
    for exclusion in corpus["known_exclusions"]:
        builder.record(
            "skipped",
            str(exclusion["route"]),
            str(exclusion["source_path"]),
            "known_exclusions",
            None,
            exclusion,
            "known_excluded_route_delegated",
        )
    for warning in corpus["warnings"]:
        builder.record("warnings", None, None, f"warnings:{warning['file']}", None, warning["detail"], str(warning["issue"]))
    for context in contexts_by_url.values():
        for warning_index, warning in enumerate(context.page["warnings"]):
            builder.record(
                "warnings",
                context.url,
                str(context.page["corpus_path"]),
                f"warnings[{warning_index}]",
                warning_index + 1,
                warning["detail"],
                str(warning["issue"]),
            )


def report_sort_key(record: Mapping[str, Any]) -> tuple[str, str, str, int, str, str]:
    """Return the contract's deterministic extraction-report ordering."""
    return (
        str(record.get("pageUrl") or ""),
        str(record.get("category") or ""),
        str(record.get("sourcePath") or ""),
        int(record["sourceOrdinal"]) if isinstance(record.get("sourceOrdinal"), int) else -1,
        str(record.get("reason") or ""),
        stable_json(record.get("value")),
    )


def _build_stats(corpus: Mapping[str, Any], nodes: Sequence[JsonObject], edges: Sequence[JsonObject], reports: Mapping[str, Sequence[JsonObject]]) -> JsonObject:
    """Build deterministic graph, evidence, source, and disposition counts."""
    nodes_by_class = Counter(str(node["class"]) for node in nodes)
    edges_by_relation = Counter(str(edge["relation"]) for edge in edges)
    nodes_by_inventory = Counter(str(node["inventoryId"]) for node in nodes)
    edges_by_inventory = Counter(str(edge["inventoryId"]) for edge in edges)
    page_types = Counter(
        str(node["attributes"].get("pageType") or "null")
        for node in nodes
        if node["class"] == "DocumentationPage" and node["curationStatus"] == CURATED
    )
    source_components = Counter(
        str(item["component"])
        for page in corpus["pages"]
        for item in page["external_content_sources"]
    )
    return {
        "inputPageCount": len(corpus["pages"]),
        "inputHeadingCount": sum(len(page["headings"]) for page in corpus["pages"]),
        "inputLinkCount": sum(len(page["links"]) for page in corpus["pages"]),
        "inputTagOccurrenceCount": sum(len(page["tags"]) for page in corpus["pages"]),
        "inputAuthorOccurrenceCount": sum(len(page["authors"]) for page in corpus["pages"]),
        "inputExternalContentSourceCount": sum(len(page["external_content_sources"]) for page in corpus["pages"]),
        "nodeCount": len(nodes),
        "edgeCount": len(edges),
        "evidenceSpanCount": len(nodes) + len(edges),
        "nodesByClass": dict(sorted(nodes_by_class.items())),
        "edgesByRelation": dict(sorted(edges_by_relation.items())),
        "nodesByInventoryId": dict(sorted(nodes_by_inventory.items())),
        "edgesByInventoryId": dict(sorted(edges_by_inventory.items())),
        "pageTypes": dict(sorted(page_types.items())),
        "externalContentSourcesByComponent": dict(sorted(source_components.items())),
        "curatedNodeCount": sum(node["curationStatus"] == CURATED for node in nodes),
        "referencedNodeCount": sum(node["curationStatus"] == REFERENCED for node in nodes),
        "referencedRepositoryCount": sum(node["class"] == "Repository" and node["curationStatus"] == REFERENCED for node in nodes),
        "referencedDatasetResourceCount": sum(node["class"] == "DatasetResource" and node["curationStatus"] == REFERENCED for node in nodes),
        "referencedDocumentationPageCount": sum(node["class"] == "DocumentationPage" and node["curationStatus"] == REFERENCED for node in nodes),
        "sourceRepoFileCount": nodes_by_class["RepoFile"],
        "deferredCount": len(reports["deferred"]),
        "skippedCount": len(reports["skipped"]),
        "unresolvedCount": len(reports["unresolved"]),
        "warningCount": len(reports["warnings"]),
        "phaseAWarningCount": len(corpus["warnings"]) + sum(len(page["warnings"]) for page in corpus["pages"]),
    }


def _build_output(
    corpus: Mapping[str, Any],
    source_corpus_sha256: str,
    source_repository_url: str,
    source_repository_ref: str,
    ontology: OntologyRegistry,
    builder: GraphBuilder,
) -> JsonObject:
    """Assemble sorted graph, report arrays, metadata, stats, and validation marker."""
    nodes = [builder.nodes[node_id].to_dict() for node_id in sorted(builder.nodes)]
    edges = [builder.edges[edge_id].to_dict() for edge_id in sorted(builder.edges)]
    reports = {
        report_type: sorted(records.values(), key=report_sort_key)
        for report_type, records in builder.reports.items()
    }
    return {
        "schema_version": OUTPUT_SCHEMA_VERSION,
        "phase_b_version": PHASE_B_VERSION,
        "source_schema_version": corpus["schema_version"],
        "source_phase_a_version": corpus["phase_a_version"],
        "source_type": SOURCE_TYPE,
        "source_corpus_sha256": source_corpus_sha256,
        "source_repository": {"url": source_repository_url, "ref": source_repository_ref},
        "ontology": {
            "specPath": "src/ontology/ontology_spec.yaml",
            "version": ontology.version,
            "sha256": ontology.sha256,
        },
        "nodes": nodes,
        "edges": edges,
        "deferred": reports["deferred"],
        "skipped": reports["skipped"],
        "unresolved": reports["unresolved"],
        "warnings": reports["warnings"],
        "stats": _build_stats(corpus, nodes, edges, reports),
        "validation": {"valid": True, "issues": []},
    }


def _allowed_types(value: Any) -> set[str]:
    """Normalize one ontology domain/range declaration to a class-name set."""
    if isinstance(value, list):
        return {str(item) for item in value}
    return {str(value)}


def _validate_evidence(evidence: Any, owner: str, issues: list[str]) -> None:
    """Validate complete public evidence and separation from internal paths."""
    if not isinstance(evidence, dict):
        issues.append(f"{owner}: evidence must be an object")
        return
    actual_keys = set(evidence)
    if actual_keys != EVIDENCE_REQUIRED_KEYS:
        issues.append(
            f"{owner}: evidence keys differ: "
            f"missing={sorted(EVIDENCE_REQUIRED_KEYS - actual_keys)}, "
            f"extra={sorted(actual_keys - EVIDENCE_REQUIRED_KEYS)}"
        )
        return
    for key in ("evidenceText", "sourceLocation", "extractionMethod", "sourceArtifact", "version"):
        if not nonempty_text(evidence.get(key)):
            issues.append(f"{owner}: evidence.{key} is empty")
    for key in ("sourceLocation", "sourceArtifact"):
        location = str(evidence.get(key) or "")
        if not location.startswith(("https://", "http://")):
            issues.append(f"{owner}: evidence.{key} is not public HTTP(S): {location!r}")
        lowered = location.casefold()
        if "data/raw" in lowered or "data/interim" in lowered or "ciroh_hub_corpus.json" in lowered:
            issues.append(f"{owner}: evidence.{key} exposes internal pipeline path")
    if evidence.get("extractionMethod") != EXTRACTION_METHOD:
        issues.append(f"{owner}: evidence extractionMethod is not deterministic")


def validate_output(
    output: Mapping[str, Any],
    corpus: Mapping[str, Any],
    ontology: OntologyRegistry | None = None,
    validate_frozen_snapshot: bool = False,
) -> list[str]:
    """Validate graph shape, ontology compatibility, provenance, and Phase A reconciliation."""
    ontology = ontology or load_ontology_registry()
    issues: list[str] = []
    nodes = output.get("nodes")
    edges = output.get("edges")
    if not isinstance(nodes, list) or not isinstance(edges, list):
        return ["nodes and edges must be arrays"]
    node_ids = [str(node.get("id")) for node in nodes if isinstance(node, dict)]
    edge_ids = [str(edge.get("id")) for edge in edges if isinstance(edge, dict)]
    if len(node_ids) != len(set(node_ids)):
        issues.append("duplicate node IDs")
    if len(edge_ids) != len(set(edge_ids)):
        issues.append("duplicate edge IDs")
    if node_ids != sorted(node_ids):
        issues.append("nodes are not sorted by ID")
    if edge_ids != sorted(edge_ids):
        issues.append("edges are not sorted by ID")
    node_by_id = {str(node.get("id")): node for node in nodes if isinstance(node, dict)}
    for node in nodes:
        if not isinstance(node, dict):
            issues.append("node is not an object")
            continue
        missing = NODE_REQUIRED_KEYS - set(node)
        if missing:
            issues.append(f"{node.get('id')}: node missing keys {sorted(missing)}")
            continue
        if node["curationStatus"] not in {CURATED, REFERENCED}:
            issues.append(f"{node['id']}: invalid curationStatus")
        inventory = ontology.classes_by_id.get(str(node["inventoryId"]))
        if inventory is None:
            issues.append(f"{node['id']}: unknown class inventory ID {node['inventoryId']}")
        elif inventory.get("name") != node["class"]:
            issues.append(f"{node['id']}: class does not match inventory ID {node['inventoryId']}")
        if node["class"] in FORBIDDEN_NODE_CLASSES:
            issues.append(f"{node['id']}: forbidden LLM-reserved class {node['class']}")
        _validate_evidence(node.get("evidence"), str(node["id"]), issues)
    for edge in edges:
        if not isinstance(edge, dict):
            issues.append("edge is not an object")
            continue
        missing = EDGE_REQUIRED_KEYS - set(edge)
        if missing:
            issues.append(f"{edge.get('id')}: edge missing keys {sorted(missing)}")
            continue
        source = node_by_id.get(str(edge["source"]))
        target = node_by_id.get(str(edge["target"]))
        if source is None or target is None:
            issues.append(f"{edge['id']}: dangling endpoint source={edge['source']!r}, target={edge['target']!r}")
        relation = ontology.relations_by_id.get(str(edge["inventoryId"]))
        if relation is None:
            issues.append(f"{edge['id']}: unknown relation inventory ID {edge['inventoryId']}")
        elif relation.get("name") != edge["relation"]:
            issues.append(f"{edge['id']}: relation does not match inventory ID {edge['inventoryId']}")
        elif source is not None and target is not None:
            domains = _allowed_types(relation.get("domain"))
            ranges = _allowed_types(relation.get("range"))
            if "owl:Thing" not in domains and source["class"] not in domains:
                issues.append(f"{edge['id']}: domain violation {source['class']} not in {sorted(domains)}")
            if target["class"] not in ranges:
                issues.append(f"{edge['id']}: range violation {target['class']} not in {sorted(ranges)}")
        if edge["relation"] in FORBIDDEN_RELATIONS:
            issues.append(f"{edge['id']}: forbidden or undeclared relation {edge['relation']}")
        _validate_evidence(edge.get("evidence"), str(edge["id"]), issues)
    curated_pages = [node for node in nodes if node.get("class") == "DocumentationPage" and node.get("curationStatus") == CURATED]
    if len(curated_pages) != len(corpus["pages"]):
        issues.append("curated DocumentationPage count does not match Phase A pages")
    expected_page_ids = {make_page_id(str(page["canonical_url"])) for page in corpus["pages"]}
    if {node["id"] for node in curated_pages} != expected_page_ids:
        issues.append("curated DocumentationPage IDs do not exactly match Phase A pages")
    page_by_url = {str(page["canonical_url"]): page for page in corpus["pages"]}
    for canonical_url, page in page_by_url.items():
        page_id = make_page_id(canonical_url)
        page_node = node_by_id.get(page_id)
        if page_node is not None and page_node.get("attributes") != _page_attributes(page, derive_page_type(page)):
            issues.append(f"{canonical_url}: DocumentationPage attributes do not match Phase A")
        identifier_id = make_exact_identifier_id("page_url", canonical_url)
        identifier = node_by_id.get(identifier_id)
        if identifier is None or identifier.get("class") != "Identifier" or identifier.get("attributes") != {
            "idType": "page_url",
            "value": canonical_url,
            "normalizedValue": canonical_url,
        }:
            issues.append(f"{canonical_url}: canonical page URL Identifier is missing or malformed")
        matching_identifier_edges = [
            edge
            for edge in edges
            if edge.get("relation") == "hasIdentifier"
            and edge.get("source") == page_id
            and edge.get("target") == identifier_id
        ]
        if len(matching_identifier_edges) != 1:
            issues.append(f"{canonical_url}: expected exactly one canonical page hasIdentifier edge")
    expected_file_ids = {
        make_source_file_id(str(output["source_repository"]["url"]), str(page["source_path"]))
        for page in corpus["pages"]
    }
    actual_file_ids = {node["id"] for node in nodes if node.get("class") == "RepoFile"}
    if actual_file_ids != expected_file_ids:
        issues.append("RepoFile nodes do not exactly match distinct source_path values")
    if any(
        str(node.get("attributes", {}).get("path", "")).startswith("_generated_js_pages/")
        for node in nodes
        if node.get("class") == "RepoFile"
    ):
        issues.append("materialized generated MDX path incorrectly became a RepoFile")
    expected_section_ids = {
        make_section_id(str(page["canonical_url"]), int(heading["ordinal"]))
        for page in corpus["pages"]
        for heading in page["headings"]
    }
    expected_link_ids = {
        make_link_id(str(page["canonical_url"]), int(link["ordinal"]))
        for page in corpus["pages"]
        for link in page["links"]
    }
    if {node["id"] for node in nodes if node.get("class") == "Section"} != expected_section_ids:
        issues.append("Section nodes do not exactly match Phase A headings")
    if {node["id"] for node in nodes if node.get("class") == "Link"} != expected_link_ids:
        issues.append("Link nodes do not exactly match Phase A links")
    for page in corpus["pages"]:
        canonical_url = str(page["canonical_url"])
        section_ids = {
            int(heading["ordinal"]): make_section_id(canonical_url, int(heading["ordinal"]))
            for heading in page["headings"]
        }
        for heading in page["headings"]:
            ordinal = int(heading["ordinal"])
            section = node_by_id.get(section_ids[ordinal])
            expected_attributes = {
                "pageUrl": canonical_url,
                "ordinal": ordinal,
                "level": heading["level"],
                "text": heading["text"],
                "rawText": heading["raw_text"],
                "sourceLine": heading["source_line"],
                "parentHeadingOrdinal": heading["parent_heading_ordinal"],
                "parentSectionId": section_ids.get(heading["parent_heading_ordinal"]),
            }
            if section is not None and section.get("attributes") != expected_attributes:
                issues.append(f"{canonical_url}: Section {ordinal} attributes do not match Phase A")
        for link in page["links"]:
            ordinal = int(link["ordinal"])
            link_node = node_by_id.get(make_link_id(canonical_url, ordinal))
            expected_attributes = {
                "pageUrl": canonical_url,
                "ordinal": ordinal,
                "anchorText": link["anchor_text"],
                "rawTarget": link["raw_target"],
                "resolvedUrl": link["resolved_url"],
                "linkType": link["link_type"],
                "sourceLine": link["source_line"],
                "headingOrdinal": link["heading_ordinal"],
                "sectionId": section_ids.get(link["heading_ordinal"]),
            }
            if link_node is not None and link_node.get("attributes") != expected_attributes:
                issues.append(f"{canonical_url}: Link {ordinal} attributes do not match Phase A")
    expected_relations = {
        "hasSourceFile": len(corpus["pages"]),
        "hasSection": sum(len(page["headings"]) for page in corpus["pages"]),
        "linksTo": sum(len(page["links"]) for page in corpus["pages"]),
        "hasSubject": sum(bool(normalize_text_key(str(tag))) for page in corpus["pages"] for tag in page["tags"]),
        "hasContributor": sum(bool(str(author.get("name") or "").strip()) for page in corpus["pages"] for author in page["authors"]),
        "affiliatedWith": sum(bool(str(author.get("name") or "").strip()) and bool(str(author.get("affiliation") or "").strip()) for page in corpus["pages"] for author in page["authors"]),
        "isPartOf": sum(page["parent_url"] is not None for page in corpus["pages"]),
        "hasSubPage": sum(page["parent_url"] is not None for page in corpus["pages"]),
    }
    actual_relation_counts = Counter(str(edge["relation"]) for edge in edges)
    for relation, expected in expected_relations.items():
        if actual_relation_counts[relation] != expected:
            issues.append(f"{relation} count {actual_relation_counts[relation]} does not match expected {expected}")
    source_file_by_path = {
        str(node["attributes"]["path"]): node for node in nodes if node.get("class") == "RepoFile"
    }
    for page in corpus["pages"]:
        source_file = source_file_by_path.get(str(page["source_path"]))
        if source_file is None:
            continue
        attrs = source_file["attributes"]
        if page["generated_from_js"]:
            if not str(page["source_path"]).endswith(".js") or attrs.get("sourceHashAvailable") is not False or attrs.get("downloaded") is not False:
                issues.append(f"{page['canonical_url']}: generated source-file semantics are invalid")
        elif attrs.get("fileSha256") != page["file_sha256"] or attrs.get("downloaded") is not True:
            issues.append(f"{page['canonical_url']}: direct source-file semantics are invalid")
    source_repository_nodes = [
        node
        for node in nodes
        if node.get("class") == "Repository"
        and node.get("attributes", {}).get("role") == "ciroh_hub_source_repository"
    ]
    if len(source_repository_nodes) != 1:
        issues.append("expected exactly one configured CIROH Hub source Repository")
    elif {
        edge["target"]
        for edge in edges
        if edge.get("relation") == "hasFile" and edge.get("source") == source_repository_nodes[0]["id"]
    } != actual_file_ids:
        issues.append("source Repository hasFile edges do not own every RepoFile exactly")
    identifier_owner_ids = {
        edge["source"]
        for edge in edges
        if edge.get("relation") == "hasIdentifier"
        and node_by_id.get(str(edge.get("target")), {}).get("class") == "Identifier"
    }
    for node in nodes:
        if node.get("class") == "Repository":
            repository_url = str(node.get("attributes", {}).get("htmlUrl") or "")
            if normalize_github_repo_url(repository_url) != repository_url:
                issues.append(f"{node['id']}: malformed referenced Repository URL {repository_url!r}")
            if node["id"] not in identifier_owner_ids:
                issues.append(f"{node['id']}: exact Repository target lacks hasIdentifier")
        elif node.get("class") == "DatasetResource":
            resource_id = str(node.get("attributes", {}).get("resourceId") or "")
            if not re.fullmatch(r"[0-9a-f]{32}", resource_id):
                issues.append(f"{node['id']}: malformed HydroShare resource identifier")
            if node["id"] not in identifier_owner_ids:
                issues.append(f"{node['id']}: exact DatasetResource target lacks hasIdentifier")
        elif node.get("class") == "DocumentationPage" and node.get("curationStatus") == REFERENCED:
            if node["id"] not in identifier_owner_ids:
                issues.append(f"{node['id']}: referenced DocumentationPage lacks hasIdentifier")
        elif node.get("class") == "Identifier":
            attributes = node.get("attributes", {})
            id_type = attributes.get("idType")
            normalized_value = str(attributes.get("normalizedValue") or "")
            if id_type == "page_url" and normalize_hub_url(normalized_value) != normalized_value:
                issues.append(f"{node['id']}: malformed page URL Identifier")
            elif id_type == "github_repository_url" and normalize_github_repo_url(normalized_value) != normalized_value:
                issues.append(f"{node['id']}: malformed GitHub repository Identifier")
            elif id_type == "hydroshare_resource_id" and not re.fullmatch(r"[0-9a-f]{32}", normalized_value):
                issues.append(f"{node['id']}: malformed HydroShare Identifier")
    line_counts = {
        str(page["corpus_path"]): len(str(page["content_mdx"]).splitlines())
        for page in corpus["pages"]
    }
    for owner in nodes + edges:
        lineage = owner.get("internalLineage")
        if not isinstance(lineage, dict) or not nonempty_text(lineage.get("phaseAField")):
            issues.append(f"{owner.get('id')}: internalLineage is missing phaseAField")
            continue
        if lineage.get("phaseAVersion") != corpus["phase_a_version"]:
            issues.append(f"{owner.get('id')}: internalLineage phaseAVersion mismatch")
        source_line = lineage.get("sourceLine")
        corpus_path = lineage.get("corpusPath")
        if source_line is not None and (
            not isinstance(source_line, int)
            or corpus_path not in line_counts
            or not 1 <= source_line <= line_counts[str(corpus_path)]
        ):
            issues.append(f"{owner.get('id')}: internalLineage sourceLine is invalid")
    for report_type in ("deferred", "skipped", "unresolved", "warnings"):
        records = output.get(report_type)
        if not isinstance(records, list):
            issues.append(f"{report_type} must be an array")
        elif records != sorted(records, key=report_sort_key):
            issues.append(f"{report_type} is not deterministically sorted")
    phase_a_warning_count = len(corpus["warnings"]) + sum(len(page["warnings"]) for page in corpus["pages"])
    if len(output.get("warnings", [])) != phase_a_warning_count:
        issues.append("Phase A warnings were not propagated exactly once")
    expected_stats = _build_stats(
        corpus,
        nodes,
        edges,
        {key: output.get(key, []) for key in ("deferred", "skipped", "unresolved", "warnings")},
    )
    if output.get("stats") != expected_stats:
        issues.append("stats do not reconcile with graph and report arrays")
    if output.get("validation") != {"valid": True, "issues": []}:
        issues.append("validation report does not declare a clean successful artifact")
    if validate_frozen_snapshot:
        anchors = {
            "DocumentationPage": 242,
            "RepoFile": 242,
            "Section": 1583,
            "Link": 1767,
            "Subject": 125,
            "Person": 119,
            "Organization": 119,
        }
        class_counts = Counter(str(node["class"]) for node in nodes if not (node["class"] == "DocumentationPage" and node["curationStatus"] == REFERENCED))
        for class_name, expected in anchors.items():
            if class_counts[class_name] != expected:
                issues.append(f"frozen {class_name} count {class_counts[class_name]} != {expected}")
        if actual_relation_counts["hasIdentifier"] < 242:
            issues.append("frozen output lacks page URL hasIdentifier edges")
        component_counts = Counter(item["component"] for page in corpus["pages"] for item in page["external_content_sources"])
        if component_counts != Counter({"GitHubReadme": 49, "GitHubWikiPage": 1}):
            issues.append(f"frozen external component counts changed: {dict(component_counts)}")
    return issues


class OutputValidationError(ValueError):
    """Raised when the generated Hub Phase B graph fails validation."""

    def __init__(self, issues: Sequence[str]) -> None:
        """Store actionable issues and format a concise exception."""
        self.issues = list(issues)
        super().__init__("CIROH Hub Phase B validation failed:\n- " + "\n- ".join(self.issues))


def extract_corpus(
    corpus: JsonObject,
    source_corpus_sha256: str | None = None,
    source_repository_url: str = DEFAULT_SOURCE_REPOSITORY_URL,
    source_repository_ref: str = DEFAULT_SOURCE_REPOSITORY_REF,
    ontology: OntologyRegistry | None = None,
    validate_frozen_snapshot: bool = False,
) -> JsonObject:
    """Run complete two-pass deterministic CIROH Hub Phase B extraction."""
    validate_input_corpus(corpus)
    ontology = ontology or load_ontology_registry()
    normalized_repository_url = normalize_github_repo_url(source_repository_url)
    if normalized_repository_url is None:
        raise ValueError(f"Source repository URL is not an exact GitHub repository: {source_repository_url!r}")
    if not source_repository_ref.strip():
        raise ValueError("Source repository ref must be nonempty")
    source_hash = source_corpus_sha256 or sha256_bytes(
        (json.dumps(corpus, indent=2, ensure_ascii=False, sort_keys=True) + "\n").encode("utf-8")
    )
    pages = sorted(corpus["pages"], key=lambda page: (str(page["canonical_url"]), str(page["corpus_path"])))
    contexts = [
        PageContext(page, make_page_id(str(page["canonical_url"])), derive_page_type(page), str(corpus["phase_a_version"]))
        for page in pages
    ]
    contexts_by_url = {context.url: context for context in contexts}
    page_aliases = build_hub_page_alias_index(pages)
    normalized_excluded_routes = {
        normalized
        for exclusion in corpus["known_exclusions"]
        if (normalized := normalize_hub_url(str(exclusion["route"])))
    }
    known_excluded_routes = set(normalized_excluded_routes)
    for route in normalized_excluded_routes:
        if route != "https://hub.ciroh.org/":
            known_excluded_routes.add(route[:-1] if route.endswith("/") else route + "/")
    builder = GraphBuilder(str(corpus["phase_a_version"]))
    subject_declarations: dict[str, list[JsonObject]] = defaultdict(list)
    for context in contexts:
        _emit_page_local_nodes(context, builder, subject_declarations)
    _emit_subject_nodes(subject_declarations, contexts_by_url, builder)
    source_repository_id, _ = _emit_source_repository_and_files(
        pages,
        contexts_by_url,
        normalized_repository_url,
        source_repository_ref,
        builder,
    )
    _emit_hierarchy(contexts, contexts_by_url, builder)
    _emit_exact_targets_and_relations(
        contexts,
        contexts_by_url,
        page_aliases,
        known_excluded_routes,
        normalized_repository_url,
        source_repository_id,
        builder,
    )
    _propagate_reports(corpus, contexts_by_url, builder)
    output = _build_output(
        corpus,
        source_hash,
        normalized_repository_url,
        source_repository_ref,
        ontology,
        builder,
    )
    issues = validate_output(output, corpus, ontology, validate_frozen_snapshot)
    if issues:
        raise OutputValidationError(issues)
    return output


def serialize_deterministically(output: Mapping[str, Any]) -> bytes:
    """Serialize output as stable UTF-8 indented JSON with a final newline."""
    return (json.dumps(output, indent=2, ensure_ascii=False, sort_keys=True) + "\n").encode("utf-8")


def write_output(output: Mapping[str, Any], path: Path) -> None:
    """Create parent directories and write the validated deterministic artifact."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(serialize_deterministically(output))


def reason_frequencies(records: Sequence[Mapping[str, Any]]) -> dict[str, int]:
    """Count report reasons in deterministic key order."""
    return dict(sorted(Counter(str(record["reason"]) for record in records).items()))


def print_report(output: Mapping[str, Any]) -> None:
    """Print the complete extraction and validation summary without page contents."""
    stats = output["stats"]
    print("CIROH Hub Phase B validation report")
    print(f"schema_version: {output['schema_version']}")
    print(f"phase_b_version: {output['phase_b_version']}")
    print(f"source_schema_version: {output['source_schema_version']}")
    print(f"source_phase_a_version: {output['source_phase_a_version']}")
    print(f"source corpus SHA-256: {output['source_corpus_sha256']}")
    print(f"pages processed: {stats['inputPageCount']}")
    print(f"nodes: {stats['nodeCount']}")
    print(f"edges: {stats['edgeCount']}")
    print(f"EvidenceSpans: {stats['evidenceSpanCount']}")
    print(f"nodes by class: {json.dumps(stats['nodesByClass'], sort_keys=True)}")
    print(f"nodes by formal ID: {json.dumps(stats['nodesByInventoryId'], sort_keys=True)}")
    print(f"edges by relation: {json.dumps(stats['edgesByRelation'], sort_keys=True)}")
    print(f"edges by formal ID: {json.dumps(stats['edgesByInventoryId'], sort_keys=True)}")
    print(f"page types: {json.dumps(stats['pageTypes'], sort_keys=True)}")
    print(f"curated nodes: {stats['curatedNodeCount']}")
    print(f"referenced nodes: {stats['referencedNodeCount']}")
    for report_type in ("deferred", "skipped", "unresolved", "warnings"):
        print(f"{report_type}: {len(output[report_type])} {json.dumps(reason_frequencies(output[report_type]), sort_keys=True)}")
    print("valid: True")


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    """Parse CLI arguments for deterministic CIROH Hub extraction."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT, help="Phase A Hub corpus JSON path.")
    parser.add_argument("--out", "--output", dest="output", type=Path, default=DEFAULT_OUTPUT, help="Phase B output JSON path.")
    parser.add_argument("--source-repository-url", default=DEFAULT_SOURCE_REPOSITORY_URL)
    parser.add_argument("--source-repository-ref", default=DEFAULT_SOURCE_REPOSITORY_REF)
    parser.add_argument("--ontology-spec", type=Path, default=DEFAULT_ONTOLOGY_SPEC)
    parser.add_argument("--validate-frozen-snapshot", action="store_true")
    parser.add_argument("--report", action="store_true")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> None:
    """Load Phase A, extract, validate, and write only a successful artifact."""
    args = parse_args(argv)
    try:
        corpus, source_hash = load_corpus(args.input)
        ontology = load_ontology_registry(args.ontology_spec)
        output = extract_corpus(
            corpus,
            source_hash,
            args.source_repository_url,
            args.source_repository_ref,
            ontology,
            args.validate_frozen_snapshot,
        )
        write_output(output, args.output)
        if args.report:
            print_report(output)
            print(f"output path: {args.output}")
            print(f"output SHA-256: {sha256_bytes(serialize_deterministically(output))}")
    except (OSError, ValueError, yaml.YAMLError) as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
