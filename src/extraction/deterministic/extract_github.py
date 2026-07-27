"""Extract deterministic GitHub ontology mentions from the Phase A corpus.

This offline Phase B transformer reads only the consolidated GitHub Phase A
JSON and writes a self-contained nodes/edges artifact. It does not reopen raw
repositories, read repository contents, make network calls, execute code, call
an LLM, consolidate identities, or load a graph database.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence
from urllib.parse import unquote, urlparse, urlunparse, quote

from packaging.utils import canonicalize_name


PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_INPUT = PROJECT_ROOT / "data/interim/coderepos/ciroh_github_corpus.json"
DEFAULT_OUTPUT = PROJECT_ROOT / "data/interim/coderepos/github_nodes_edges.json"
SUPPORTED_SOURCE_SCHEMAS = frozenset({"1.1.0"})
OUTPUT_SCHEMA_VERSION = "1.0.0"
PHASE_B_VERSION = "1.0.0"
SOURCE_TYPE = "github"
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
ARTICLE_LIKE_CFF_TYPES = frozenset(
    {
        "article",
        "conference-paper",
        "proceedings",
        "report",
        "thesis",
        "book",
        "book-chapter",
        "conference",
        "journal-article",
        "manuscript",
        "preprint",
    }
)
DATASET_CFF_TYPES = frozenset({"dataset", "data", "data-set"})
SOFTWARE_CFF_TYPES = frozenset(
    {
        "software",
        "software-code",
        "software-container",
        "software-executable",
        "software-library",
        "software-module",
        "software-package",
        "computer-program",
    }
)
IMPLEMENTATION_URL_KEYS = frozenset(
    {"code", "repository", "repository_code", "source", "source_code"}
)
SPDX_IDENTIFIERS = {
    identifier.casefold(): identifier
    for identifier in (
        "Apache-2.0",
        "BSD-2-Clause",
        "BSD-3-Clause",
        "CC-BY-4.0",
        "CC0-1.0",
        "EPL-2.0",
        "GPL-2.0-only",
        "GPL-2.0-or-later",
        "GPL-3.0-only",
        "GPL-3.0-or-later",
        "ISC",
        "LGPL-2.1-only",
        "LGPL-2.1-or-later",
        "LGPL-3.0-only",
        "LGPL-3.0-or-later",
        "MIT",
        "MPL-2.0",
        "Unlicense",
    )
}
SCOPE_ORDER = {"root": 0, "docs": 1, "example": 2}
LOCAL_SOURCE_NAMES = (
    "files_manifest.json",
    "repo_metadata.json",
    "contributors.json",
    "archive_info.json",
)
IMAGE_SUFFIXES = (".svg", ".png", ".jpg", ".jpeg", ".gif", ".webp")
DOI_RE = re.compile(r"10\.\d{4,9}/[^\s<>\"'?#]+", re.IGNORECASE)
HYDROSHARE_RE = re.compile(
    r"(?:https?://)?(?:www\.)?hydroshare\.org/resource/([0-9a-f]{32})(?:/|$|[?#])",
    re.IGNORECASE,
)
ORCID_RE = re.compile(r"(?:https?://orcid\.org/)?(\d{4}-\d{4}-\d{4}-\d{3}[\dX])", re.IGNORECASE)


# Every fixed Phase A object shape is declared here so unknown fields fail
# accounting validation instead of disappearing silently.
ACCOUNTED_FIELDS: dict[str, frozenset[str]] = {
    "top": frozenset({"schema_version", "repos"}),
    "repo": frozenset(
        {
            "repo_id",
            "name",
            "full_name",
            "html_url",
            "description",
            "homepage",
            "default_branch",
            "language",
            "topics",
            "fork",
            "fork_parent",
            "archived",
            "disabled",
            "visibility",
            "timestamps",
            "github_stats",
            "archive",
            "license",
            "identifiers",
            "contributors",
            "files",
            "dependencies",
            "repo_dependencies",
            "execution_environment",
            "citation",
            "citation_md",
            "software_metadata",
            "readme",
            "provenance",
        }
    ),
    "timestamps": frozenset({"created_at", "updated_at", "pushed_at"}),
    "github_stats": frozenset(
        {"size_kb", "stargazers_count", "watchers_count", "forks_count", "open_issues_count"}
    ),
    "archive": frozenset({"frozen_commit_sha", "downloaded_at_epoch", "archive_format"}),
    "license": frozenset({"key", "name", "spdx_id", "url", "is_spdx", "source_path"}),
    "identifier": frozenset({"id_type", "value", "source_path"}),
    "contributor": frozenset(
        {"github_id", "login", "html_url", "type", "contributions", "is_bot", "source_path"}
    ),
    "files": frozenset(
        {
            "total_count",
            "downloaded_count",
            "selection_reason_histogram",
            "has_dockerfile",
            "inventory",
            "downloaded",
            "dockerfiles",
        }
    ),
    "file_inventory": frozenset(
        {
            "path",
            "file_name",
            "extension",
            "size_bytes",
            "downloaded",
            "selection_reason",
            "file_role",
            "source_path",
        }
    ),
    "downloaded_file": frozenset(
        {
            "path",
            "file_name",
            "extension",
            "size_bytes",
            "downloaded",
            "selection_reason",
            "file_role",
            "source_path",
        }
    ),
    "dockerfile": frozenset({"path", "file_name", "size_bytes"}),
    "dependency": frozenset(
        {
            "name",
            "raw",
            "version_spec",
            "extras",
            "marker",
            "ecosystem",
            "dep_group",
            "is_vcs",
            "sources",
        }
    ),
    "repo_dependency": frozenset(
        {
            "name",
            "raw",
            "version_spec",
            "extras",
            "marker",
            "ecosystem",
            "dep_group",
            "is_vcs",
            "vcs_url",
            "ref",
            "subdirectory",
            "egg",
            "sources",
        }
    ),
    "dependency_source": frozenset(
        {"manifest_path", "manifest_type", "manifest_scope", "raw_line"}
    ),
    "environment": frozenset(
        {
            "kind",
            "name",
            "channels",
            "python_version",
            "prefix",
            "is_lock",
            "pinned_count",
            "pinned_set_evidence",
            "source_path",
        }
    ),
    "citation": frozenset(
        {
            "present",
            "format",
            "placeholder",
            "source_path",
            "cff_version",
            "type",
            "title",
            "software_authors",
            "doi",
            "version",
            "date_released",
            "url",
            "repository_code",
            "repository",
            "keywords",
            "license",
            "abstract",
            "preferred_citation",
            "references",
        }
    ),
    "cff_software_author": frozenset(
        {"family_names", "given_names", "orcid", "affiliation", "email"}
    ),
    "citation_reference": frozenset(
        {
            "type",
            "authors",
            "doi",
            "title",
            "journal",
            "year",
            "volume",
            "number",
            "start",
            "end",
            "publisher",
            "url",
        }
    ),
    "citation_author": frozenset({"family_names", "given_names", "orcid"}),
    "citation_md": frozenset({"present", "source_path", "deferred_to_llm"}),
    "software_metadata": frozenset(
        {"name", "version", "authors", "urls", "license", "manifest_type", "source_path"}
    ),
    "software_author": frozenset({"name", "email"}),
    "readme": frozenset({"present", "source_path", "text", "deterministic_urls"}),
    "readme_urls": frozenset({"hydroshare", "github", "dois", "other"}),
    "provenance": frozenset(
        {"source_artifact", "phase_a_version", "manifest_classifications", "parse_warnings"}
    ),
    "parse_warning": frozenset({"file", "issue"}),
}


JsonObject = dict[str, Any]


def stable_json(value: Any) -> str:
    """Serialize a value canonically for comparison, sorting, and hashing."""
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def stable_hash(value: str) -> str:
    """Return the first 20 lowercase hexadecimal characters of SHA-256."""
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:20]


def make_stable_id(prefix: str, value: str) -> str:
    """Build a deterministic source-scoped ID from a prefix and discriminator."""
    return f"{prefix}:{stable_hash(value)}"


def make_edge_id(source: str, relation: str, target: str) -> str:
    """Build a deterministic edge ID from semantic edge identity."""
    return f"github:edge:{relation}:{stable_hash(f'{source}|{relation}|{target}') }"


def sorted_unique(values: Iterable[Any]) -> list[Any]:
    """Return JSON-distinct values sorted by their canonical serialization."""
    by_key = {stable_json(value): value for value in values}
    return [by_key[key] for key in sorted(by_key)]


def nonempty_text(value: Any) -> str:
    """Convert a structured value to stable, non-whitespace evidence text."""
    if isinstance(value, str):
        return value.strip()
    if value is None:
        return ""
    return stable_json(value)


def normalize_name(value: str | None) -> str:
    """Normalize a verbatim name only for deterministic comparison keys."""
    return " ".join(str(value or "").split()).casefold()


def normalize_orcid(value: str | None) -> str | None:
    """Normalize an ORCID URL or identifier without validating checksum semantics."""
    if not value:
        return None
    match = ORCID_RE.search(value.strip())
    return match.group(1).upper() if match else None


def normalize_github_repo_url(value: str | None) -> str | None:
    """Normalize recognized GitHub repository roots to HTTPS without network access."""
    if not value:
        return None
    raw = value.strip()
    if raw.startswith("git+"):
        raw = raw[4:]
    if raw.startswith("git@github.com:"):
        raw = "https://github.com/" + raw.removeprefix("git@github.com:")
    elif raw.startswith("ssh://git@github.com/"):
        raw = "https://github.com/" + raw.removeprefix("ssh://git@github.com/")
    parsed = urlparse(raw)
    if parsed.scheme not in {"http", "https"} or parsed.netloc.casefold() not in {
        "github.com",
        "www.github.com",
    }:
        return None
    parts = [unquote(part) for part in parsed.path.strip("/").split("/") if part]
    if len(parts) != 2:
        return None
    owner, repository = parts
    if repository.endswith(".git"):
        repository = repository[:-4]
    if not owner or not repository or repository in {".", ".."}:
        return None
    return f"https://github.com/{owner}/{repository}"


def github_repo_key(value: str | None) -> str | None:
    """Return a case-insensitive owner/repository lookup key for a GitHub root URL."""
    normalized = normalize_github_repo_url(value)
    if not normalized:
        return None
    return urlparse(normalized).path.strip("/").casefold()


def classify_github_url(value: str | None) -> str:
    """Classify a GitHub-like URL mechanically without assigning graph semantics."""
    if not value:
        return "unrecognized"
    raw = value.strip()
    parsed = urlparse(raw.removeprefix("git+"))
    host = parsed.netloc.casefold()
    if host in {"raw.githubusercontent.com", "objects.githubusercontent.com"}:
        return "raw_asset"
    if host.endswith("githubusercontent.com") or "/assets/" in parsed.path:
        return "user_attachment"
    if normalize_github_repo_url(raw):
        return "repository_root"
    if host not in {"github.com", "www.github.com"}:
        return "unrecognized"
    parts = [part for part in parsed.path.strip("/").split("/") if part]
    if len(parts) < 3:
        return "unrecognized"
    category = parts[2].casefold()
    if category in {"issues", "pull", "pulls"}:
        return "issues"
    if category in {"actions", "workflows"} or raw.casefold().endswith("badge.svg"):
        return "actions_badge"
    if category in {"blob", "tree"}:
        return "blob_tree"
    return "unrecognized"


def normalize_doi(value: str | None) -> str | None:
    """Normalize a DOI candidate and reject badge/image false positives."""
    if not value:
        return None
    raw = unquote(value.strip())
    lowered = raw.casefold()
    if "shields.io" in lowered or "/badge/" in lowered or lowered.endswith(IMAGE_SUFFIXES):
        return None
    raw = re.sub(r"^doi:\s*", "", raw, flags=re.IGNORECASE)
    raw = re.sub(r"^https?://(?:dx\.)?doi\.org/", "", raw, flags=re.IGNORECASE)
    match = DOI_RE.search(raw)
    if not match:
        return None
    doi = match.group(0).rstrip(".,;:)]}").casefold()
    if doi.endswith(IMAGE_SUFFIXES):
        return None
    return doi if re.fullmatch(r"10\.\d{4,9}/\S+", doi) else None


def extract_hydroshare_resource_id(value: str | None) -> str | None:
    """Extract an exact 32-character HydroShare resource identifier from a URL."""
    if not value:
        return None
    match = HYDROSHARE_RE.search(value.strip())
    return match.group(1).lower() if match else None


def canonicalize_package_name(name: str | None, ecosystem: str | None = "pypi") -> str:
    """Canonicalize a package name according to its declared ecosystem."""
    raw = str(name or "").strip()
    if str(ecosystem or "").casefold() == "pypi":
        return str(canonicalize_name(raw))
    return re.sub(r"[-_.]+", "-", raw.casefold())


def build_blob_url(html_url: str, frozen_commit_sha: str, repository_path: str) -> str:
    """Build a SHA-pinned GitHub blob URL with segment-wise path encoding."""
    if not repository_path or repository_path.startswith("/"):
        raise ValueError(f"Repository path must be non-empty and relative: {repository_path!r}")
    encoded_path = "/".join(quote(segment, safe="") for segment in repository_path.split("/"))
    return f"{html_url.rstrip('/')}/blob/{frozen_commit_sha}/{encoded_path}"


def build_api_url(full_name: str, contributors: bool = False) -> str:
    """Build a public GitHub API URL without making an HTTP request."""
    suffix = "/contributors" if contributors else ""
    return f"https://api.github.com/repos/{quote(full_name, safe='/')}{suffix}"


def is_concrete_version(value: Any) -> bool:
    """Return whether a version is a concrete literal rather than an expression."""
    if value is None:
        return False
    text = str(value).strip()
    if not text or text.casefold().startswith("attr:"):
        return False
    expression_markers = ("${", "{{", "}}", "__version__", "<dynamic>", "unknown")
    return not any(marker in text.casefold() for marker in expression_markers)


def source_sort_key(source: Mapping[str, Any]) -> tuple[int, str, str]:
    """Return the contract ordering key for a Phase A source declaration."""
    return (
        SCOPE_ORDER.get(str(source.get("manifest_scope") or ""), 99),
        str(source.get("manifest_path") or ""),
        str(source.get("raw_line") or ""),
    )


def select_primary_source(sources: Sequence[Mapping[str, Any]]) -> tuple[JsonObject, list[JsonObject]]:
    """Select primary evidence and return all declarations in deterministic order."""
    if not sources:
        raise ValueError("At least one source declaration is required")
    ordered = [dict(source) for source in sorted(sources, key=source_sort_key)]
    return ordered[0], ordered


@dataclass(frozen=True)
class Evidence:
    """Public EvidenceSpan-compatible payload for a node or edge."""

    evidence_text: str
    source_location: str
    source_artifact: str
    version: str | int | float
    extraction_method: str = EXTRACTION_METHOD

    def to_dict(self) -> JsonObject:
        """Return the contract evidence shape."""
        return {
            "evidenceText": self.evidence_text,
            "sourceLocation": self.source_location,
            "extractionMethod": self.extraction_method,
            "sourceArtifact": self.source_artifact,
            "version": self.version,
        }


@dataclass(frozen=True)
class SoftwareLicenseDisposition:
    """Normalized interpretation of a Phase A software-license value."""

    kind: str
    normalized_value: str | None
    original_value: Any

    @property
    def is_text_declaration(self) -> bool:
        """Return whether this value identifies license terms directly."""
        return self.kind == "text" and bool(self.normalized_value)


@dataclass(frozen=True)
class ArchiveDoiDisposition:
    """Deterministic repository DOI sets used for archive-candidate resolution."""

    repository_identifier_dois: tuple[str, ...]
    paper_typed_dois: tuple[str, ...]
    dataset_typed_dois: tuple[str, ...]
    eligible_archive_candidates: tuple[str, ...]
    typing_contexts: tuple[tuple[str, str, str], ...]

    def contexts_for(self, doi: str) -> tuple[str, ...]:
        """Return stable structured typing descriptions for one normalized DOI."""
        return tuple(
            f"{target_class}: {source_field}"
            for typed_doi, target_class, source_field in self.typing_contexts
            if typed_doi == doi
        )


def build_archive_doi_disposition(repo: Mapping[str, Any]) -> ArchiveDoiDisposition:
    """Classify repository DOI identifiers without relying on graph-emission order."""
    repository_dois = {
        normalized
        for identifier in repo["identifiers"]
        if identifier["id_type"] == "doi"
        and (normalized := normalize_doi(str(identifier["value"])))
    }
    paper_contexts: dict[str, set[str]] = defaultdict(set)
    dataset_contexts: dict[str, set[str]] = defaultdict(set)
    citation = repo["citation"]
    if citation["present"] and citation["format"] == "cff" and not citation["placeholder"]:
        preferred = citation["preferred_citation"]
        preferred_doi = normalize_doi(preferred["doi"])
        preferred_type = str(preferred["type"] or "").casefold()
        if preferred_doi and preferred_type in ARTICLE_LIKE_CFF_TYPES:
            paper_contexts[preferred_doi].add("citation.preferred_citation.doi")
        for reference_index, reference in enumerate(citation["references"]):
            reference_doi = normalize_doi(reference["doi"])
            if not reference_doi:
                continue
            reference_type = str(reference["type"] or "").casefold()
            source_field = f"citation.references[{reference_index}].doi"
            if reference_type in ARTICLE_LIKE_CFF_TYPES:
                paper_contexts[reference_doi].add(source_field)
            elif reference_type in DATASET_CFF_TYPES:
                dataset_contexts[reference_doi].add(source_field)
    paper_dois = set(paper_contexts)
    dataset_dois = set(dataset_contexts)
    eligible = repository_dois - paper_dois - dataset_dois
    typing_contexts = tuple(
        sorted(
            (doi, target_class, source_field)
            for target_class, contexts in (
                ("Paper", paper_contexts),
                ("DatasetResource", dataset_contexts),
            )
            for doi, source_fields in contexts.items()
            for source_field in source_fields
        )
    )
    return ArchiveDoiDisposition(
        repository_identifier_dois=tuple(sorted(repository_dois)),
        paper_typed_dois=tuple(sorted(paper_dois)),
        dataset_typed_dois=tuple(sorted(dataset_dois)),
        eligible_archive_candidates=tuple(sorted(eligible)),
        typing_contexts=typing_contexts,
    )


@dataclass(frozen=True)
class InternalLineage:
    """Internal Phase A lineage kept separate from public evidence."""

    phase_a_field: str
    phase_a_version: str
    raw_source: str | None = None

    def to_dict(self) -> JsonObject:
        """Return the stable internal-lineage shape."""
        payload: JsonObject = {
            "phaseAField": self.phase_a_field,
            "phaseAVersion": self.phase_a_version,
        }
        if self.raw_source:
            payload["rawSource"] = self.raw_source
        return payload


@dataclass(frozen=True)
class Node:
    """A deterministic Phase B node record."""

    id: str
    class_name: str
    inventory_id: str
    attributes: JsonObject
    canonical_key: str
    identity_regime: str
    curation_status: str
    evidence: Evidence
    internal_lineage: InternalLineage

    def to_dict(self) -> JsonObject:
        """Return the required JSON node shape."""
        return {
            "id": self.id,
            "class": self.class_name,
            "inventoryId": self.inventory_id,
            "attributes": self.attributes,
            "canonicalKey": self.canonical_key,
            "identityRegime": self.identity_regime,
            "curationStatus": self.curation_status,
            "evidence": self.evidence.to_dict(),
            "internalLineage": self.internal_lineage.to_dict(),
        }


@dataclass(frozen=True)
class Edge:
    """A deterministic Phase B edge record."""

    id: str
    relation: str
    inventory_id: str
    source: str
    target: str
    attributes: JsonObject
    evidence: Evidence
    internal_lineage: InternalLineage

    def to_dict(self) -> JsonObject:
        """Return the required JSON edge shape."""
        return {
            "id": self.id,
            "relation": self.relation,
            "inventoryId": self.inventory_id,
            "source": self.source,
            "target": self.target,
            "attributes": self.attributes,
            "evidence": self.evidence.to_dict(),
            "internalLineage": self.internal_lineage.to_dict(),
        }


@dataclass
class RepoContext:
    """Frequently used deterministic values for one Phase A repository."""

    repo: JsonObject
    repo_id: int
    repo_name: str
    full_name: str
    html_url: str
    sha: str
    acquisition_epoch: int | float
    phase_a_version: str
    repo_node_id: str
    snapshot_url: str
    metadata_api_url: str
    contributors_api_url: str
    identifier_ids: list[str] = field(default_factory=list)
    file_ids: list[str] = field(default_factory=list)
    dependency_ids: list[str] = field(default_factory=list)
    package_dependency_records: list[JsonObject] = field(default_factory=list)
    environment_ids: list[str] = field(default_factory=list)
    contributor_ids: list[str] = field(default_factory=list)
    cff_author_ids: list[str] = field(default_factory=list)
    package_author_ids: list[str] = field(default_factory=list)
    organization_links: list[JsonObject] = field(default_factory=list)
    tool_records: list[JsonObject] = field(default_factory=list)
    version_records: list[JsonObject] = field(default_factory=list)
    license_records: list[JsonObject] = field(default_factory=list)

    @classmethod
    def from_repo(cls, repo: JsonObject, source_schema_version: str) -> "RepoContext":
        """Validate required identity fields and build a repository context."""
        repo_id = repo.get("repo_id")
        full_name = repo.get("full_name")
        html_url = repo.get("html_url")
        sha = (repo.get("archive") or {}).get("frozen_commit_sha")
        epoch = (repo.get("archive") or {}).get("downloaded_at_epoch")
        if not isinstance(repo_id, int) or not full_name or not html_url or not sha:
            raise ValueError(
                "Repository requires integer repo_id, full_name, html_url, and frozen_commit_sha: "
                f"{repo.get('name')!r}"
            )
        if epoch is None:
            raise ValueError(f"Repository lacks acquisition epoch: {repo.get('name')!r}")
        repo_name = str(repo.get("name") or full_name.split("/", 1)[-1])
        expected_snapshot_url = f"{str(html_url).rstrip('/')}/tree/{sha}"
        declared_snapshot_url = (repo.get("provenance") or {}).get("source_artifact")
        if declared_snapshot_url != expected_snapshot_url:
            raise ValueError(
                f"Repository provenance.source_artifact mismatch for {repo_name!r}: "
                f"expected {expected_snapshot_url!r}, got {declared_snapshot_url!r}"
            )
        return cls(
            repo=repo,
            repo_id=repo_id,
            repo_name=repo_name,
            full_name=str(full_name),
            html_url=str(html_url).rstrip("/"),
            sha=str(sha),
            acquisition_epoch=epoch,
            phase_a_version=str((repo.get("provenance") or {}).get("phase_a_version") or source_schema_version),
            repo_node_id=f"github:repo:{repo_id}",
            snapshot_url=expected_snapshot_url,
            metadata_api_url=build_api_url(str(full_name)),
            contributors_api_url=build_api_url(str(full_name), contributors=True),
        )

    def file_evidence(self, text: Any, path: str) -> Evidence:
        """Build SHA-pinned public evidence for a repository file."""
        return Evidence(
            evidence_text=nonempty_text(text),
            source_location=build_blob_url(self.html_url, self.sha, path),
            source_artifact=self.snapshot_url,
            version=self.sha,
        )

    def metadata_evidence(self, text: Any) -> Evidence:
        """Build public evidence for repository API metadata."""
        return Evidence(
            evidence_text=nonempty_text(text),
            source_location=self.metadata_api_url,
            source_artifact=self.html_url,
            version=self.acquisition_epoch,
        )

    def contributor_evidence(self, text: Any) -> Evidence:
        """Build public evidence for contributor API metadata."""
        return Evidence(
            evidence_text=nonempty_text(text),
            source_location=self.contributors_api_url,
            source_artifact=self.html_url,
            version=self.acquisition_epoch,
        )

    def lineage(self, field_path: str, raw_source: str | None = None) -> InternalLineage:
        """Build internal Phase A lineage for a normalized value."""
        return InternalLineage(field_path, self.phase_a_version, raw_source)


class GraphBuilder:
    """Accumulate deterministic graph and report records with conflict detection."""

    def __init__(self) -> None:
        """Initialize empty node, edge, report, and repository indices."""
        self.nodes: dict[str, Node] = {}
        self.edges: dict[str, Edge] = {}
        self.reports: dict[str, dict[str, JsonObject]] = {
            "deferred": {},
            "skipped": {},
            "unresolved": {},
            "warnings": {},
        }
        self.repo_by_id: dict[int, str] = {}
        self.repo_by_url: dict[str, str] = {}
        self.repo_by_full_name: dict[str, str] = {}
        self.external_repo_cache: dict[tuple[int, str], str] = {}
        self.dataset_cache: dict[tuple[int, str, str], str] = {}

    def emit_node(self, node: Node) -> str:
        """Emit a node or fail when its deterministic ID has conflicting content."""
        existing = self.nodes.get(node.id)
        if existing is not None and existing != node:
            raise ValueError(f"Conflicting node content for deterministic ID {node.id}")
        self.nodes[node.id] = node
        return node.id

    def emit_edge(self, edge: Edge) -> str:
        """Emit an edge or fail when its semantic ID has conflicting content."""
        existing = self.edges.get(edge.id)
        if existing is not None and existing != edge:
            raise ValueError(f"Conflicting edge content for deterministic ID {edge.id}")
        self.edges[edge.id] = edge
        return edge.id

    def add_edge(
        self,
        relation: str,
        inventory_id: str,
        source: str,
        target: str,
        attributes: JsonObject,
        evidence: Evidence,
        lineage: InternalLineage,
    ) -> str:
        """Construct and emit a semantic edge."""
        edge = Edge(
            id=make_edge_id(source, relation, target),
            relation=relation,
            inventory_id=inventory_id,
            source=source,
            target=target,
            attributes=attributes,
            evidence=evidence,
            internal_lineage=lineage,
        )
        return self.emit_edge(edge)

    def record(
        self,
        report_type: str,
        context: RepoContext,
        source_path: str | None,
        value: Any,
        reason: str,
    ) -> None:
        """Record one deterministic deferred/skipped/unresolved/warning disposition."""
        record = {
            "repoId": context.repo_id,
            "repoName": context.repo_name,
            "category": report_type.removesuffix("s"),
            "sourcePath": source_path,
            "value": value,
            "reason": reason,
        }
        self.reports[report_type][stable_json(record)] = record

    def record_deferred(self, context: RepoContext, source_path: str | None, value: Any, reason: str) -> None:
        """Record evidence intentionally deferred to a later semantic layer."""
        self.record("deferred", context, source_path, value, reason)

    def record_skipped(self, context: RepoContext, source_path: str | None, value: Any, reason: str) -> None:
        """Record input intentionally excluded by a deterministic rule."""
        self.record("skipped", context, source_path, value, reason)

    def record_unresolved(self, context: RepoContext, source_path: str | None, value: Any, reason: str) -> None:
        """Record an expected deterministic target that could not be resolved."""
        self.record("unresolved", context, source_path, value, reason)

    def record_warning(self, context: RepoContext, source_path: str | None, value: Any, reason: str) -> None:
        """Record a deterministic warning without dropping source evidence."""
        self.record("warnings", context, source_path, value, reason)


def _assert_object_keys(value: Any, shape: str, location: str) -> JsonObject:
    """Validate a fixed Phase A object shape and return it as a dictionary."""
    if not isinstance(value, dict):
        raise ValueError(f"{location} must be an object")
    expected = ACCOUNTED_FIELDS[shape]
    actual = set(value)
    if actual != expected:
        missing = sorted(expected - actual)
        unknown = sorted(actual - expected)
        raise ValueError(f"Unaccounted Phase A fields at {location}: missing={missing}, unknown={unknown}")
    return value


def validate_input_field_accounting(corpus: JsonObject) -> None:
    """Ensure every fixed Phase A field is covered by the disposition matrix."""
    _assert_object_keys(corpus, "top", "corpus")
    repos = corpus.get("repos")
    if not isinstance(repos, list):
        raise ValueError("Phase A corpus repos must be an array")
    for repo_index, repo_value in enumerate(repos):
        repo = _assert_object_keys(repo_value, "repo", f"repos[{repo_index}]")
        for field_name, shape in (
            ("timestamps", "timestamps"),
            ("github_stats", "github_stats"),
            ("archive", "archive"),
            ("files", "files"),
            ("citation", "citation"),
            ("readme", "readme"),
            ("provenance", "provenance"),
        ):
            _assert_object_keys(repo[field_name], shape, f"repos[{repo_index}].{field_name}")
        if repo["license"] is not None:
            _assert_object_keys(repo["license"], "license", f"repos[{repo_index}].license")
        for field_name, shape in (
            ("identifiers", "identifier"),
            ("contributors", "contributor"),
            ("dependencies", "dependency"),
            ("repo_dependencies", "repo_dependency"),
            ("execution_environment", "environment"),
            ("software_metadata", "software_metadata"),
        ):
            values = repo[field_name]
            if not isinstance(values, list):
                raise ValueError(f"repos[{repo_index}].{field_name} must be an array")
            for item_index, item in enumerate(values):
                checked = _assert_object_keys(
                    item, shape, f"repos[{repo_index}].{field_name}[{item_index}]"
                )
                if field_name in {"dependencies", "repo_dependencies"}:
                    for source_index, source in enumerate(checked["sources"]):
                        _assert_object_keys(
                            source,
                            "dependency_source",
                            f"repos[{repo_index}].{field_name}[{item_index}].sources[{source_index}]",
                        )
                if field_name == "software_metadata":
                    if not isinstance(checked["urls"], dict):
                        raise ValueError("software_metadata.urls must be an object")
                    for author_index, author in enumerate(checked["authors"]):
                        _assert_object_keys(
                            author,
                            "software_author",
                            f"repos[{repo_index}].software_metadata[{item_index}].authors[{author_index}]",
                        )
        files = repo["files"]
        for field_name, shape in (
            ("inventory", "file_inventory"),
            ("downloaded", "downloaded_file"),
            ("dockerfiles", "dockerfile"),
        ):
            for item_index, item in enumerate(files[field_name]):
                _assert_object_keys(
                    item, shape, f"repos[{repo_index}].files.{field_name}[{item_index}]"
                )
        citation = repo["citation"]
        for author_index, author in enumerate(citation["software_authors"]):
            _assert_object_keys(
                author,
                "cff_software_author",
                f"repos[{repo_index}].citation.software_authors[{author_index}]",
            )
        preferred = _assert_object_keys(
            citation["preferred_citation"],
            "citation_reference",
            f"repos[{repo_index}].citation.preferred_citation",
        )
        for author_index, author in enumerate(preferred["authors"]):
            _assert_object_keys(
                author,
                "citation_author",
                f"repos[{repo_index}].citation.preferred_citation.authors[{author_index}]",
            )
        for reference_index, reference in enumerate(citation["references"]):
            checked_reference = _assert_object_keys(
                reference,
                "citation_reference",
                f"repos[{repo_index}].citation.references[{reference_index}]",
            )
            for author_index, author in enumerate(checked_reference["authors"]):
                _assert_object_keys(
                    author,
                    "citation_author",
                    f"repos[{repo_index}].citation.references[{reference_index}].authors[{author_index}]",
                )
        if repo["citation_md"] is not None:
            _assert_object_keys(repo["citation_md"], "citation_md", f"repos[{repo_index}].citation_md")
        _assert_object_keys(
            repo["readme"]["deterministic_urls"],
            "readme_urls",
            f"repos[{repo_index}].readme.deterministic_urls",
        )
        for warning_index, warning_value in enumerate(repo["provenance"]["parse_warnings"]):
            _assert_object_keys(
                warning_value,
                "parse_warning",
                f"repos[{repo_index}].provenance.parse_warnings[{warning_index}]",
            )


def load_corpus(path: Path) -> JsonObject:
    """Load and validate a supported Phase A consolidated corpus."""
    try:
        corpus = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"Unable to load Phase A corpus {path}: {exc}") from exc
    if not isinstance(corpus, dict):
        raise ValueError("Phase A corpus root must be an object")
    schema_version = corpus.get("schema_version")
    if schema_version not in SUPPORTED_SOURCE_SCHEMAS:
        raise ValueError(
            f"Unsupported Phase A schema version {schema_version!r}; "
            f"supported={sorted(SUPPORTED_SOURCE_SCHEMAS)}"
        )
    validate_input_field_accounting(corpus)
    return corpus


def make_node(
    node_id: str,
    class_name: str,
    inventory_id: str,
    attributes: JsonObject,
    canonical_key: str,
    identity_regime: str,
    curation_status: str,
    evidence: Evidence,
    lineage: InternalLineage,
) -> Node:
    """Construct a node with the complete required Phase B shape."""
    return Node(
        id=node_id,
        class_name=class_name,
        inventory_id=inventory_id,
        attributes=attributes,
        canonical_key=canonical_key,
        identity_regime=identity_regime,
        curation_status=curation_status,
        evidence=evidence,
        internal_lineage=lineage,
    )


def emit_node(builder: GraphBuilder, node: Node) -> str:
    """Emit a node through the project conflict-detecting graph builder."""
    return builder.emit_node(node)


def emit_edge(builder: GraphBuilder, edge: Edge) -> str:
    """Emit an edge through the project conflict-detecting graph builder."""
    return builder.emit_edge(edge)


def record_deferred(
    builder: GraphBuilder,
    context: RepoContext,
    source_path: str | None,
    value: Any,
    reason: str,
) -> None:
    """Record a deterministic deferred disposition."""
    builder.record_deferred(context, source_path, value, reason)


def record_skipped(
    builder: GraphBuilder,
    context: RepoContext,
    source_path: str | None,
    value: Any,
    reason: str,
) -> None:
    """Record a deterministic skipped disposition."""
    builder.record_skipped(context, source_path, value, reason)


def record_unresolved(
    builder: GraphBuilder,
    context: RepoContext,
    source_path: str | None,
    value: Any,
    reason: str,
) -> None:
    """Record a deterministic unresolved disposition."""
    builder.record_unresolved(context, source_path, value, reason)


def record_warning(
    builder: GraphBuilder,
    context: RepoContext,
    source_path: str | None,
    value: Any,
    reason: str,
) -> None:
    """Record a deterministic warning disposition."""
    builder.record_warning(context, source_path, value, reason)


def repository_path_from_lineage(value: str | None) -> str | None:
    """Extract a repository-relative file path from a Phase A lineage value."""
    if not value:
        return None
    text = str(value)
    if text.startswith(tuple(f"{name}:" for name in LOCAL_SOURCE_NAMES)):
        if text.startswith("files_manifest.json:"):
            return text.split(":", 1)[1]
        return None
    if ":" in text:
        prefix = text.split(":", 1)[0]
        if "." in Path(prefix).name:
            return prefix
    return text


def repository_node(context: RepoContext) -> Node:
    """Build N1, the curated repository node."""
    repo = context.repo
    timestamps = repo["timestamps"]
    attributes = {
        "repoId": context.repo_id,
        "name": repo["name"],
        "fullName": context.full_name,
        "htmlUrl": context.html_url,
        "description": repo["description"],
        "homepage": repo["homepage"],
        "defaultBranch": repo["default_branch"],
        "language": repo["language"],
        "topics": sorted(repo["topics"]),
        "fork": repo["fork"],
        "forkParent": repo["fork_parent"],
        "archived": repo["archived"],
        "disabled": repo["disabled"],
        "visibility": repo["visibility"],
        "createdAt": timestamps["created_at"],
        "updatedAt": timestamps["updated_at"],
        "pushedAt": timestamps["pushed_at"],
        "githubStats": repo["github_stats"],
        "archiveFormat": repo["archive"]["archive_format"],
        "fileTotalCount": repo["files"]["total_count"],
        "downloadedFileCount": repo["files"]["downloaded_count"],
        "selectionReasonHistogram": repo["files"]["selection_reason_histogram"],
        "hasDockerfile": repo["files"]["has_dockerfile"],
        "declaredLicenseMetadata": repo["license"],
        "metricExclusion": ["administrative"],
    }
    return make_node(
        context.repo_node_id,
        "Repository",
        "A-C01",
        attributes,
        f"github-repo-id:{context.repo_id}",
        "github_numeric_id",
        CURATED,
        context.metadata_evidence(context.full_name),
        context.lineage("repo root"),
    )


def register_repository_context(context: RepoContext, builder: GraphBuilder) -> None:
    """Index and emit a curated repository independent of input ordering."""
    if context.repo_id in builder.repo_by_id:
        raise ValueError(f"Duplicate GitHub repository ID {context.repo_id}")
    normalized_url = normalize_github_repo_url(context.html_url)
    if not normalized_url:
        raise ValueError(f"Repository html_url is not a GitHub root: {context.html_url}")
    url_key = normalized_url.casefold()
    full_name_key = context.full_name.casefold()
    if url_key in builder.repo_by_url or full_name_key in builder.repo_by_full_name:
        raise ValueError(f"Duplicate curated GitHub repository target {context.full_name}")
    builder.repo_by_id[context.repo_id] = context.repo_node_id
    builder.repo_by_url[url_key] = context.repo_node_id
    builder.repo_by_full_name[full_name_key] = context.repo_node_id
    emit_node(builder, repository_node(context))


def normalized_identifier_value(id_type: str, value: Any) -> str:
    """Normalize a repository identifier for an exact canonical key."""
    text = str(value or "").strip()
    kind = id_type.casefold()
    if kind == "repo_url":
        return normalize_github_repo_url(text) or text
    if kind == "doi":
        return normalize_doi(text) or text.casefold()
    if kind == "commit_sha":
        return text.casefold()
    return text


def identifier_evidence(context: RepoContext, identifier: JsonObject) -> Evidence:
    """Choose public evidence for a Phase A repository identifier."""
    id_type = str(identifier["id_type"])
    value = identifier["value"]
    source_path = str(identifier["source_path"])
    if id_type == "repo_url":
        return Evidence(
            nonempty_text(value),
            normalize_github_repo_url(str(value)) or context.html_url,
            context.html_url,
            context.acquisition_epoch,
        )
    if id_type == "commit_sha":
        return Evidence(nonempty_text(value), context.snapshot_url, context.snapshot_url, context.sha)
    repository_path = repository_path_from_lineage(source_path)
    if repository_path:
        return context.file_evidence(value, repository_path)
    return context.metadata_evidence(value)


def seed_identifiers(context: RepoContext, builder: GraphBuilder) -> None:
    """Create N2 repository Identifier mentions."""
    for index, identifier in enumerate(context.repo["identifiers"]):
        id_type = str(identifier["id_type"])
        value = identifier["value"]
        source_path = str(identifier["source_path"])
        normalized = normalized_identifier_value(id_type, value)
        node_id = (
            f"github:identifier:{context.repo_id}:"
            f"{stable_hash(f'{id_type}|{value}|{source_path}')}"
        )
        node = make_node(
            node_id,
            "Identifier",
            "A-ID01",
            {"idType": id_type, "value": value, "normalizedValue": normalized, "sourceRepoId": context.repo_id},
            f"{id_type.casefold()}:{normalized}",
            "exact_identifier",
            CURATED,
            identifier_evidence(context, identifier),
            context.lineage(f"identifiers[{index}]", source_path),
        )
        emit_node(builder, node)
        context.identifier_ids.append(node_id)


def seed_files(context: RepoContext, builder: GraphBuilder) -> None:
    """Create N3 File nodes exclusively from the authoritative inventory."""
    for file_entry in context.repo["files"]["inventory"]:
        path = str(file_entry["path"])
        node_id = f"github:file:{context.repo_id}:{stable_hash(path)}"
        attributes = {
            "sourceRepoId": context.repo_id,
            "path": path,
            "fileName": file_entry["file_name"],
            "extension": file_entry["extension"],
            "sizeBytes": file_entry["size_bytes"],
            "downloaded": file_entry["downloaded"],
            "contentAvailable": file_entry["downloaded"],
            "selectionReason": file_entry["selection_reason"],
            "fileRole": file_entry["file_role"],
        }
        node = make_node(
            node_id,
            "File",
            "A-C02",
            attributes,
            f"github-file:{context.repo_id}:{path}",
            "repository_relative_path",
            CURATED,
            context.file_evidence(path, path),
            context.lineage(
                f"files.inventory[path={path}]",
                str(file_entry["source_path"]),
            ),
        )
        emit_node(builder, node)
        context.file_ids.append(node_id)


def seed_package_dependencies(context: RepoContext, builder: GraphBuilder) -> None:
    """Create N4 source-scoped package Dependency mentions."""
    for index, dependency in enumerate(context.repo["dependencies"]):
        ecosystem = str(dependency["ecosystem"] or "unknown").casefold()
        canonical_name = canonicalize_package_name(dependency["name"], ecosystem)
        node_id = (
            f"github:dependency:{context.repo_id}:"
            f"{stable_hash(f'{ecosystem}|{canonical_name}')}"
        )
        primary, declarations = select_primary_source(dependency["sources"])
        source_path = str(primary["manifest_path"])
        evidence_text = primary.get("raw_line") or dependency["raw"] or dependency["name"]
        node = make_node(
            node_id,
            "Dependency",
            "A-C03",
            {
                "sourceRepoId": context.repo_id,
                "name": dependency["name"],
                "canonicalName": canonical_name,
                "ecosystem": ecosystem,
                "isVcs": False,
            },
            f"package:{ecosystem}:{canonical_name}",
            "ecosystem_package_name",
            CURATED,
            context.file_evidence(evidence_text, source_path),
            context.lineage(f"dependencies[{index}]", source_path),
        )
        emit_node(builder, node)
        context.dependency_ids.append(node_id)
        context.package_dependency_records.append(
            {
                "dependency": dependency,
                "nodeId": node_id,
                "primarySource": primary,
                "sourceDeclarations": declarations,
                "phaseAIndex": index,
            }
        )


def environment_descriptor(environment: JsonObject) -> str:
    """Build a concise deterministic evidence descriptor for an environment."""
    kind = str(environment["kind"])
    if environment["is_lock"]:
        return f"{kind}: {environment['pinned_count'] or 0} pinned packages"
    parts = [kind]
    if environment["name"]:
        parts.append(str(environment["name"]))
    if environment["python_version"]:
        parts.append(f"python={environment['python_version']}")
    return ": ".join(parts[:2]) + (f"; {parts[2]}" if len(parts) > 2 else "")


def seed_execution_environments(context: RepoContext, builder: GraphBuilder) -> None:
    """Create N6 ExecutionEnvironment nodes from Phase A parsed records only."""
    for index, environment in enumerate(context.repo["execution_environment"]):
        kind = str(environment["kind"])
        source_path = str(environment["source_path"])
        node_id = f"github:env:{context.repo_id}:{stable_hash(f'{kind}|{source_path}')}"
        node = make_node(
            node_id,
            "ExecutionEnvironment",
            "A-C04",
            {
                "sourceRepoId": context.repo_id,
                "kind": kind,
                "name": environment["name"],
                "channels": sorted(environment["channels"]),
                "pythonVersion": environment["python_version"],
                "prefix": environment["prefix"],
                "isLock": environment["is_lock"],
                "pinnedCount": environment["pinned_count"],
                "pinnedSetEvidence": environment["pinned_set_evidence"],
                "sourcePath": source_path,
                "metricExclusion": ["pinnedSetEvidence"],
            },
            f"github-env:{context.repo_id}:{kind}:{source_path}",
            "repository_manifest_path",
            CURATED,
            context.file_evidence(environment_descriptor(environment), source_path),
            context.lineage(f"execution_environment[{index}]", source_path),
        )
        emit_node(builder, node)
        context.environment_ids.append(node_id)


def seed_github_contributors(context: RepoContext, builder: GraphBuilder) -> None:
    """Create N7 human GitHub contributor mentions and report bots."""
    for index, contributor in enumerate(context.repo["contributors"]):
        source_path = str(contributor["source_path"])
        if contributor["is_bot"]:
            record_skipped(
                builder,
                context,
                source_path,
                contributor["login"],
                "bot_contributor_excluded",
            )
            continue
        login = str(contributor["login"] or "")
        github_id = contributor["github_id"]
        node_id = (
            f"github:person:{context.repo_id}:"
            f"{stable_hash(f'github|{source_path}|{github_id}|{login}')}"
        )
        canonical_key = (
            f"github-user-id:{github_id}"
            if github_id is not None
            else f"github-login:{login.casefold()}"
        )
        node = make_node(
            node_id,
            "Person",
            "A-AG01",
            {
                "sourceRepoId": context.repo_id,
                "githubId": github_id,
                "login": login,
                "profileUrl": contributor["html_url"],
                "contributions": contributor["contributions"],
                "contributorType": contributor["type"],
                "moduleRoleId": "A-C05",
            },
            canonical_key,
            "github_login",
            CURATED,
            context.contributor_evidence(
                f"{login} ({contributor['contributions']} contributions)"
            ),
            context.lineage(f"contributors[{index}]", source_path),
        )
        emit_node(builder, node)
        context.contributor_ids.append(node_id)


def cff_author_display(author: Mapping[str, Any]) -> str:
    """Build a verbatim display name from Phase A CFF author fields."""
    return " ".join(
        part for part in (str(author.get("given_names") or ""), str(author.get("family_names") or "")) if part
    ).strip()


def seed_cff_authors_and_organizations(context: RepoContext, builder: GraphBuilder) -> None:
    """Create N8 CFF software authors and N11 affiliation organizations."""
    citation = context.repo["citation"]
    if not (citation["present"] and citation["format"] == "cff") or citation["placeholder"]:
        return
    source_path = str(citation["source_path"])
    for index, author in enumerate(citation["software_authors"]):
        display_name = cff_author_display(author)
        orcid = normalize_orcid(author["orcid"])
        email = str(author["email"] or "").strip().casefold() or None
        if orcid:
            canonical_key = f"orcid:{orcid}"
            regime = "cff_orcid"
        elif email:
            canonical_key = f"email:{email}"
            regime = "cff_email"
        else:
            canonical_key = f"name:{normalize_name(display_name)}"
            regime = "cff_name"
        node_id = (
            f"github:person:{context.repo_id}:"
            f"{stable_hash(f'cff-software-author|{source_path}|{index}')}"
        )
        descriptor = display_name or orcid or email or f"CFF software author {index}"
        node = make_node(
            node_id,
            "Person",
            "A-AG01",
            {
                "sourceRepoId": context.repo_id,
                "familyNames": author["family_names"],
                "givenNames": author["given_names"],
                "displayName": display_name,
                "orcid": author["orcid"],
                "affiliation": author["affiliation"],
                "email": author["email"],
                "role": "softwareAuthor",
                "moduleRoleId": "A-C05",
            },
            canonical_key,
            regime,
            CURATED,
            context.file_evidence(descriptor, source_path),
            context.lineage(f"citation.software_authors[{index}]", source_path),
        )
        emit_node(builder, node)
        context.cff_author_ids.append(node_id)
        affiliation = str(author["affiliation"] or "").strip()
        if affiliation:
            organization_id = (
                f"github:organization:{context.repo_id}:"
                f"{stable_hash(f'{source_path}|{affiliation}')}"
            )
            organization = make_node(
                organization_id,
                "Organization",
                "A-AG02",
                {"sourceRepoId": context.repo_id, "name": affiliation},
                f"organization-name:{normalize_name(affiliation)}",
                "organization_name",
                CURATED,
                context.file_evidence(affiliation, source_path),
                context.lineage(
                    f"citation.software_authors[{index}].affiliation",
                    source_path,
                ),
            )
            existing_organization = builder.nodes.get(organization_id)
            if existing_organization is None:
                emit_node(builder, organization)
            elif (
                existing_organization.class_name != organization.class_name
                or existing_organization.inventory_id != organization.inventory_id
                or existing_organization.attributes != organization.attributes
                or existing_organization.canonical_key != organization.canonical_key
                or existing_organization.identity_regime != organization.identity_regime
                or existing_organization.curation_status != organization.curation_status
            ):
                raise ValueError(
                    f"Conflicting shared Organization content for deterministic ID {organization_id}"
                )
            context.organization_links.append(
                {
                    "personId": node_id,
                    "organizationId": organization_id,
                    "affiliation": affiliation,
                    "authorIndex": index,
                    "sourcePath": source_path,
                    "evidence": context.file_evidence(affiliation, source_path),
                    "lineage": context.lineage(
                        f"citation.software_authors[{index}].affiliation",
                        source_path,
                    ),
                }
            )


def seed_package_authors(context: RepoContext, builder: GraphBuilder) -> None:
    """Create N9 package-metadata author mentions without reparsing names."""
    for software_index, software in enumerate(context.repo["software_metadata"]):
        source_path = str(software["source_path"])
        for author_index, author in enumerate(software["authors"]):
            name = str(author["name"] or "").strip()
            email = str(author["email"] or "").strip().casefold() or None
            node_id = (
                f"github:person:{context.repo_id}:"
                f"{stable_hash(f'package-author|{source_path}|{author_index}')}"
            )
            canonical_key = f"email:{email}" if email else f"name-source:{normalize_name(name)}|{source_path}"
            node = make_node(
                node_id,
                "Person",
                "A-AG01",
                {
                    "sourceRepoId": context.repo_id,
                    "name": name,
                    "email": author["email"],
                    "role": "packageAuthor",
                    "softwareName": software["name"],
                    "manifestType": software["manifest_type"],
                    "moduleRoleId": "A-C05",
                },
                canonical_key,
                "name_email" if email else "name_only_source_scoped",
                CURATED,
                context.file_evidence(name or email or f"package author {author_index}", source_path),
                context.lineage(
                    f"software_metadata[{software_index}].authors[{author_index}]",
                    source_path,
                ),
            )
            emit_node(builder, node)
            context.package_author_ids.append(node_id)


def normalized_url_key(value: str) -> str:
    """Normalize a structured software URL key for conservative semantic routing."""
    return re.sub(r"[^a-z0-9]+", "_", value.strip().casefold()).strip("_")


def cff_is_software_context(citation: Mapping[str, Any]) -> bool:
    """Return whether a valid top-level CFF record is software-like."""
    cff_type = str(citation.get("type") or "").casefold()
    return not cff_type or cff_type in SOFTWARE_CFF_TYPES


def seed_tools_and_versions(context: RepoContext, builder: GraphBuilder) -> None:
    """Create N13 structured Tool seeds and N14 concrete ModelVersion mentions."""
    citation = context.repo["citation"]
    valid_cff = bool(
        citation["present"]
        and citation["format"] == "cff"
        and not citation["placeholder"]
        and citation["source_path"]
    )
    if valid_cff and citation["title"] and cff_is_software_context(citation):
        source_path = str(citation["source_path"])
        name = str(citation["title"])
        canonical_name = canonicalize_package_name(name)
        tool_id = f"github:tool:{context.repo_id}:{stable_hash(f'{source_path}|{canonical_name}')}"
        attributes = {
            "sourceRepoId": context.repo_id,
            "name": name,
            "title": citation["title"],
            "type": citation["type"],
            "abstract": citation["abstract"],
            "sourcePath": source_path,
            "keywords": sorted(citation["keywords"]),
            "cffVersion": citation["cff_version"],
            "dateReleased": citation["date_released"],
            "url": citation["url"],
            "repositoryCode": citation["repository_code"],
            "repository": citation["repository"],
            "declaredLicense": citation["license"],
            "sourceType": "cff",
        }
        if citation["version"] and not is_concrete_version(citation["version"]):
            attributes["versionExpression"] = citation["version"]
        emit_node(
            builder,
            make_node(
                tool_id,
                "Tool",
                "A-DOM02",
                attributes,
                f"software-name:{canonical_name}",
                "structured_software_declaration",
                CURATED,
                context.file_evidence(name, source_path),
                context.lineage("citation", source_path),
            ),
        )
        context.tool_records.append(
            {
                "toolId": tool_id,
                "softwareName": name,
                "sourcePath": source_path,
                "sourceType": "cff",
                "urls": {
                    "repository_code": citation["repository_code"],
                    "repository": citation["repository"],
                },
            }
        )
        if is_concrete_version(citation["version"]):
            seed_model_version(
                context,
                builder,
                source_path,
                name,
                str(citation["version"]),
                citation["date_released"],
                "cff",
                tool_id,
                "citation.version",
            )
        elif citation["version"]:
            record_deferred(
                builder,
                context,
                source_path,
                citation["version"],
                "dynamic_version_expression",
            )
    for software_index, software in enumerate(context.repo["software_metadata"]):
        name = str(software["name"] or "").strip()
        if not name:
            record_skipped(
                builder,
                context,
                software["source_path"],
                software,
                "software_metadata_name_missing",
            )
            continue
        source_path = str(software["source_path"])
        canonical_name = canonicalize_package_name(name)
        tool_id = f"github:tool:{context.repo_id}:{stable_hash(f'{source_path}|{canonical_name}')}"
        license_disposition = normalize_software_license_declaration(software["license"])
        attributes = {
            "sourceRepoId": context.repo_id,
            "name": name,
            "title": name,
            "manifestType": software["manifest_type"],
            "sourcePath": source_path,
            "urls": dict(sorted(software["urls"].items())),
            "declaredLicense": (
                license_disposition.normalized_value
                if license_disposition.is_text_declaration
                else None
            ),
            "declaredLicenseKind": license_disposition.kind,
            "declaredLicenseSourceValue": software["license"],
            "sourceType": "software_metadata",
        }
        if software["version"] and not is_concrete_version(software["version"]):
            attributes["versionExpression"] = software["version"]
        emit_node(
            builder,
            make_node(
                tool_id,
                "Tool",
                "A-DOM02",
                attributes,
                f"software-name:{canonical_name}",
                "structured_software_declaration",
                CURATED,
                context.file_evidence(name, source_path),
                context.lineage(f"software_metadata[{software_index}]", source_path),
            ),
        )
        context.tool_records.append(
            {
                "toolId": tool_id,
                "softwareName": name,
                "sourcePath": source_path,
                "sourceType": "software_metadata",
                "urls": dict(sorted(software["urls"].items())),
            }
        )
        if is_concrete_version(software["version"]):
            seed_model_version(
                context,
                builder,
                source_path,
                name,
                str(software["version"]),
                None,
                "software_metadata",
                tool_id,
                f"software_metadata[{software_index}].version",
            )
        elif software["version"]:
            record_deferred(
                builder,
                context,
                source_path,
                software["version"],
                "dynamic_version_expression",
            )


def seed_model_version(
    context: RepoContext,
    builder: GraphBuilder,
    source_path: str,
    software_name: str,
    version: str,
    date_released: Any,
    source_type: str,
    tool_id: str,
    phase_a_field: str,
) -> None:
    """Create one concrete N14 ModelVersion mention."""
    node_id = (
        f"github:version:{context.repo_id}:"
        f"{stable_hash(f'{source_path}|{software_name}|{version}')}"
    )
    canonical_name = canonicalize_package_name(software_name)
    emit_node(
        builder,
        make_node(
            node_id,
            "ModelVersion",
            "A-C10",
            {
                "sourceRepoId": context.repo_id,
                "version": version,
                "softwareName": software_name,
                "dateReleased": date_released,
                "sourceType": source_type,
                "sourcePath": source_path,
                "toolId": tool_id,
            },
            f"software-version:{canonical_name}:{version}",
            "structured_version_literal",
            CURATED,
            context.file_evidence(version, source_path),
            context.lineage(phase_a_field, source_path),
        ),
    )
    context.version_records.append(
        {
            "nodeId": node_id,
            "toolId": tool_id,
            "softwareName": software_name,
            "sourcePath": source_path,
            "version": version,
        }
    )


def meaningful_license_declaration(value: Any) -> str | None:
    """Return a meaningful license declaration, excluding null and NOASSERTION."""
    if value is None:
        return None
    text = str(value).strip()
    if not text or text.casefold() in {"noassertion", "none", "null"}:
        return None
    return text


def normalize_spdx_identifier(value: str | None) -> str | None:
    """Return the canonical SPDX identifier for a conservatively known declaration."""
    if not value:
        return None
    return SPDX_IDENTIFIERS.get(value.strip().casefold())


def normalize_software_license_declaration(value: Any) -> SoftwareLicenseDisposition:
    """Interpret plain or structured Phase A software-license values without guessing."""
    original_value = value
    if value is None:
        return SoftwareLicenseDisposition("absent", None, original_value)
    if isinstance(value, Mapping):
        text_value = value.get("text")
        file_value = value.get("file")
        if text_value is not None and str(text_value).strip():
            return SoftwareLicenseDisposition("text", str(text_value).strip(), original_value)
        if file_value is not None and str(file_value).strip():
            return SoftwareLicenseDisposition("file", str(file_value).strip(), original_value)
        if "text" in value:
            return SoftwareLicenseDisposition("empty_text", None, original_value)
        return SoftwareLicenseDisposition("unsupported", None, original_value)
    if not isinstance(value, str):
        return SoftwareLicenseDisposition("unsupported", None, original_value)
    text = value.strip()
    if not text:
        return SoftwareLicenseDisposition("empty_text", None, original_value)
    structured_match = re.fullmatch(
        r"\{\s*(['\"])(text|file)\1\s*:\s*(['\"])(.*?)\3\s*\}",
        text,
        flags=re.DOTALL,
    )
    if structured_match:
        field_name = structured_match.group(2)
        field_value = structured_match.group(4).strip()
        if field_name == "text":
            kind = "text" if field_value else "empty_text"
            return SoftwareLicenseDisposition(kind, field_value or None, original_value)
        return SoftwareLicenseDisposition(
            "file" if field_value else "unsupported",
            field_value or None,
            original_value,
        )
    if text.startswith("{") and text.endswith("}"):
        return SoftwareLicenseDisposition("unsupported", None, original_value)
    return SoftwareLicenseDisposition("text", text, original_value)


def seed_license_nodes(context: RepoContext, builder: GraphBuilder) -> None:
    """Create N12 scoped license declarations with precedence and conflict warnings."""
    candidates: list[JsonObject] = []
    metadata_license = context.repo["license"]
    if metadata_license is not None:
        declaration = meaningful_license_declaration(
            metadata_license["spdx_id"] or metadata_license["name"] or metadata_license["key"]
        )
        if declaration:
            candidates.append(
                {
                    "priority": 0,
                    "declaration": declaration,
                    "scope": "repository_metadata",
                    "sourceType": "github_metadata",
                    "sourcePath": metadata_license["source_path"],
                    "name": metadata_license["name"],
                    "key": metadata_license["key"],
                    "spdxId": metadata_license["spdx_id"] if metadata_license["is_spdx"] else None,
                    "url": metadata_license["url"],
                    "isSpdx": metadata_license["is_spdx"],
                    "softwareName": None,
                    "originalValue": metadata_license,
                    "declarationKind": "metadata",
                    "phaseAField": "license",
                }
            )
        else:
            record_skipped(
                builder,
                context,
                metadata_license["source_path"],
                metadata_license["spdx_id"],
                "noassertion_not_a_license",
            )
    citation = context.repo["citation"]
    valid_cff = citation["present"] and citation["format"] == "cff" and not citation["placeholder"]
    cff_declaration = meaningful_license_declaration(citation["license"]) if valid_cff else None
    if cff_declaration:
        matched_spdx = normalize_spdx_identifier(cff_declaration)
        candidates.append(
            {
                "priority": 1,
                "declaration": cff_declaration,
                "scope": "cff_software",
                "sourceType": "cff",
                "sourcePath": citation["source_path"],
                "name": cff_declaration,
                "key": None,
                "spdxId": matched_spdx,
                "url": None,
                "isSpdx": bool(matched_spdx),
                "softwareName": citation["title"],
                "originalValue": citation["license"],
                "declarationKind": "text",
                "phaseAField": "citation.license",
            }
        )
    for software_index, software in enumerate(context.repo["software_metadata"]):
        disposition = normalize_software_license_declaration(software["license"])
        source_path = str(software["source_path"])
        if disposition.kind == "absent":
            continue
        if disposition.kind == "file":
            record_deferred(
                builder,
                context,
                source_path,
                disposition.normalized_value,
                "license_file_reference_requires_content_resolution",
            )
            continue
        if disposition.kind == "empty_text":
            record_skipped(
                builder,
                context,
                source_path,
                disposition.original_value,
                "empty_structured_license_text",
            )
            continue
        if disposition.kind == "unsupported":
            record_deferred(
                builder,
                context,
                source_path,
                disposition.original_value,
                "unsupported_structured_license_mapping",
            )
            continue
        declaration = str(disposition.normalized_value)
        matched_spdx = normalize_spdx_identifier(declaration)
        candidates.append(
            {
                "priority": 2,
                "declaration": declaration,
                "scope": f"software_metadata:{software['name']}",
                "sourceType": "software_metadata",
                "sourcePath": source_path,
                "name": declaration,
                "key": None,
                "spdxId": matched_spdx,
                "url": None,
                "isSpdx": bool(matched_spdx),
                "softwareName": software["name"],
                "phaseAIndex": software_index,
                "originalValue": disposition.original_value,
                "declarationKind": disposition.kind,
                "phaseAField": f"software_metadata[{software_index}].license",
            }
        )
    grouped_candidates: dict[tuple[str, str], list[JsonObject]] = defaultdict(list)
    for candidate in candidates:
        semantic_key = " ".join(str(candidate["declaration"]).split()).casefold()
        grouped_candidates[(str(candidate["scope"]), semantic_key)].append(candidate)
    candidates = []
    for group_key in sorted(grouped_candidates):
        group = sorted(
            grouped_candidates[group_key],
            key=lambda item: (str(item["sourcePath"]), stable_json(item["originalValue"])),
        )
        primary_candidate = dict(group[0])
        primary_candidate["sourceDeclarations"] = sorted_unique(
            {
                "sourcePath": item["sourcePath"],
                "phaseAField": item["phaseAField"],
                "originalValue": item["originalValue"],
            }
            for item in group
        )
        candidates.append(primary_candidate)
    candidates.sort(
        key=lambda item: (
            item["priority"],
            str(item["sourcePath"]),
            str(item["scope"]),
        )
    )
    for index, candidate in enumerate(candidates):
        declaration = str(candidate["declaration"])
        normalized = " ".join(declaration.split()).casefold()
        source_path = str(candidate["sourcePath"])
        node_id = (
            f"github:license:{context.repo_id}:"
            f"{stable_hash(f'{candidate['scope']}|{normalized}|{source_path}')}"
        )
        if candidate["sourceType"] == "github_metadata":
            evidence = context.metadata_evidence(declaration)
            raw_source = source_path
        else:
            evidence = context.file_evidence(declaration, source_path)
            raw_source = source_path
        canonical_key = (
            f"spdx:{candidate['spdxId']}"
            if candidate["spdxId"]
            else f"license-declaration:{normalized}"
        )
        emit_node(
            builder,
            make_node(
                node_id,
                "License",
                "A-C06",
                {
                    "sourceRepoId": context.repo_id,
                    "name": candidate["name"],
                    "key": candidate["key"],
                    "spdxId": candidate["spdxId"],
                    "url": candidate["url"],
                    "isSpdx": candidate["isSpdx"],
                    "declaration": declaration,
                    "declarationScope": candidate["scope"],
                    "sourceType": candidate["sourceType"],
                    "sourcePath": source_path,
                    "declarationKind": candidate["declarationKind"],
                    "originalValue": candidate["originalValue"],
                    "sourceDeclarations": candidate["sourceDeclarations"],
                },
                canonical_key,
                "spdx" if candidate["spdxId"] else "custom_license_declaration",
                CURATED,
                evidence,
                context.lineage(candidate["phaseAField"], raw_source),
            ),
        )
        context.license_records.append({**candidate, "nodeId": node_id, "isPrimary": index == 0})
    declarations = sorted({" ".join(str(item["declaration"]).split()).casefold() for item in candidates})
    if len(declarations) > 1:
        record_warning(
            builder,
            context,
            "license declarations",
            declarations,
            "license_declaration_conflict",
        )


def seed_pass1_reports(context: RepoContext, builder: GraphBuilder) -> None:
    """Record Phase A warnings and deterministic non-semantic dispositions."""
    files = context.repo["files"]
    record_skipped(
        builder,
        context,
        "files.downloaded",
        len(files["downloaded"]),
        "derived_view_not_reprocessed",
    )
    record_skipped(
        builder,
        context,
        "files.dockerfiles",
        len(files["dockerfiles"]),
        "derived_view_not_reprocessed",
    )
    citation = context.repo["citation"]
    if citation["present"] and citation["format"] == "cff" and citation["placeholder"]:
        record_skipped(
            builder,
            context,
            citation["source_path"],
            citation["title"],
            "cff_placeholder_excluded",
        )
    citation_md = context.repo["citation_md"]
    if citation_md is not None and citation_md["present"]:
        record_deferred(
            builder,
            context,
            citation_md["source_path"],
            None,
            "citation_md_deferred_to_llm",
        )
    if context.repo["readme"]["present"] and context.repo["readme"]["text"]:
        record_deferred(
            builder,
            context,
            context.repo["readme"]["source_path"],
            "README text retained in Phase A",
            "readme_text_deferred_to_llm",
        )
    for parse_warning in context.repo["provenance"]["parse_warnings"]:
        record_warning(
            builder,
            context,
            parse_warning["file"],
            parse_warning["issue"],
            "phase_a_parse_warning",
        )


def seed_pass1_nodes(context: RepoContext, builder: GraphBuilder) -> None:
    """Create all Pass 1 local nodes and deterministic report records."""
    seed_pass1_reports(context, builder)
    seed_identifiers(context, builder)
    seed_files(context, builder)
    seed_package_dependencies(context, builder)
    seed_execution_environments(context, builder)
    seed_github_contributors(context, builder)
    seed_cff_authors_and_organizations(context, builder)
    seed_package_authors(context, builder)
    seed_tools_and_versions(context, builder)
    seed_license_nodes(context, builder)


def build_contexts(corpus: JsonObject, builder: GraphBuilder) -> list[RepoContext]:
    """Build sorted repository contexts and complete curated lookup indices."""
    repos = sorted(
        corpus["repos"],
        key=lambda repo: (str(repo["name"]).casefold(), int(repo["repo_id"])),
    )
    contexts = [RepoContext.from_repo(repo, str(corpus["schema_version"])) for repo in repos]
    for context in contexts:
        register_repository_context(context, builder)
    for context in contexts:
        seed_pass1_nodes(context, builder)
    return contexts


def edge_from_target_node(
    builder: GraphBuilder,
    relation: str,
    inventory_id: str,
    source: str,
    target: str,
    attributes: JsonObject | None = None,
) -> str:
    """Emit an edge reusing the target node's evidence and lineage."""
    node = builder.nodes[target]
    return builder.add_edge(
        relation,
        inventory_id,
        source,
        target,
        attributes or {},
        node.evidence,
        node.internal_lineage,
    )


def emit_repository_internal_edges(context: RepoContext, builder: GraphBuilder) -> None:
    """Emit E1–E9 repository-internal relations created from Pass 1 nodes."""
    for identifier_id in context.identifier_ids:
        edge_from_target_node(builder, "hasIdentifier", "C-C06", context.repo_node_id, identifier_id)
    for file_id in context.file_ids:
        edge_from_target_node(builder, "hasFile", "C-C01", context.repo_node_id, file_id)
    for record in context.package_dependency_records:
        dependency = record["dependency"]
        primary = record["primarySource"]
        source_path = str(primary["manifest_path"])
        declarations = record["sourceDeclarations"]
        attributes = {
            "raw": dependency["raw"],
            "versionSpec": dependency["version_spec"],
            "extras": sorted(dependency["extras"]),
            "marker": dependency["marker"],
            "depGroup": dependency["dep_group"],
            "ecosystem": dependency["ecosystem"],
            "manifestScopes": sorted({str(source["manifest_scope"]) for source in declarations}),
            "sourceDeclarations": declarations,
            "dependencyKind": "package",
        }
        evidence_text = primary.get("raw_line") or dependency["raw"] or dependency["name"]
        builder.add_edge(
            "dependsOn",
            "C-C02",
            context.repo_node_id,
            record["nodeId"],
            attributes,
            context.file_evidence(evidence_text, source_path),
            context.lineage(f"dependencies[{record['phaseAIndex']}]", source_path),
        )
    for environment_id in context.environment_ids:
        edge_from_target_node(
            builder,
            "hasExecutionEnvironment",
            "C-C03",
            context.repo_node_id,
            environment_id,
        )
    for contributor_id in context.contributor_ids:
        contributor = builder.nodes[contributor_id]
        edge_from_target_node(
            builder,
            "hasContributor",
            "C-C04",
            context.repo_node_id,
            contributor_id,
            {
                "role": "contributor",
                "contributions": contributor.attributes["contributions"],
            },
        )
    for author_id in context.cff_author_ids:
        edge_from_target_node(
            builder,
            "hasContributor",
            "C-C04",
            context.repo_node_id,
            author_id,
            {"role": "softwareAuthor"},
        )
    for author_id in context.package_author_ids:
        author = builder.nodes[author_id]
        edge_from_target_node(
            builder,
            "hasContributor",
            "C-C04",
            context.repo_node_id,
            author_id,
            {"role": "packageAuthor", "softwareName": author.attributes["softwareName"]},
        )
    for organization_link in context.organization_links:
        builder.add_edge(
            "affiliatedWith",
            "A-AG-R1",
            organization_link["personId"],
            organization_link["organizationId"],
            {
                "affiliation": organization_link["affiliation"],
                "authorIndex": organization_link["authorIndex"],
                "sourcePath": organization_link["sourcePath"],
            },
            organization_link["evidence"],
            organization_link["lineage"],
        )
    for license_record in context.license_records:
        license_node = builder.nodes[license_record["nodeId"]]
        builder.add_edge(
            "hasLicense",
            "C-C05",
            context.repo_node_id,
            license_record["nodeId"],
            {
                "declarationScope": license_record["scope"],
                "sourceType": license_record["sourceType"],
                "softwareName": license_record["softwareName"],
                "isPrimary": license_record["isPrimary"],
            },
            license_node.evidence,
            license_node.internal_lineage,
        )
    for version_record in context.version_records:
        version_node = builder.nodes[version_record["nodeId"]]
        builder.add_edge(
            "hasModelVersion",
            "C-C09",
            context.repo_node_id,
            version_record["nodeId"],
            {
                "toolId": version_record["toolId"],
                "softwareName": version_record["softwareName"],
            },
            version_node.evidence,
            version_node.internal_lineage,
        )


def resolve_repository_target(builder: GraphBuilder, target_url: str | None) -> str | None:
    """Resolve an exact normalized GitHub root against all curated repositories."""
    normalized = normalize_github_repo_url(target_url)
    if not normalized:
        return None
    return builder.repo_by_url.get(normalized.casefold())


def normalize_structured_repository_url(value: str | None) -> str | None:
    """Resolve a root from an explicitly repository-named structured URL field."""
    normalized = normalize_github_repo_url(value)
    if normalized:
        return normalized
    if not value:
        return None
    parsed = urlparse(str(value).strip())
    if parsed.scheme not in {"http", "https"} or parsed.netloc.casefold() not in {
        "github.com",
        "www.github.com",
    }:
        return None
    parts = [unquote(part) for part in parsed.path.strip("/").split("/") if part]
    if len(parts) >= 4 and parts[2].casefold() in {"blob", "tree"}:
        repository = parts[1][:-4] if parts[1].endswith(".git") else parts[1]
        return f"https://github.com/{parts[0]}/{repository}"
    return None


def referenced_identifier(
    context: RepoContext,
    builder: GraphBuilder,
    owner_node_id: str,
    owner_kind: str,
    id_type: str,
    value: str,
    normalized_value: str,
    evidence: Evidence,
    lineage: InternalLineage,
) -> str:
    """Create a source-scoped referenced Identifier and owner relation."""
    identifier_id = (
        f"github:identifier-ref:{context.repo_id}:"
        f"{stable_hash(f'{owner_node_id}|{id_type}|{normalized_value}')}"
    )
    emit_node(
        builder,
        make_node(
            identifier_id,
            "Identifier",
            "A-ID01",
            {
                "idType": id_type,
                "value": value,
                "normalizedValue": normalized_value,
                "sourceRepoId": context.repo_id,
            },
            f"{id_type}:{normalized_value}",
            "exact_identifier",
            REFERENCED,
            evidence,
            lineage,
        ),
    )
    relation_inventory = {"Repository": "C-C06", "Paper": "C-P04", "DatasetResource": "C-D04"}[owner_kind]
    builder.add_edge(
        "hasIdentifier",
        relation_inventory,
        owner_node_id,
        identifier_id,
        {},
        evidence,
        lineage,
    )
    return identifier_id


def resolve_or_stub_repository(
    context: RepoContext,
    builder: GraphBuilder,
    target_url: str,
    evidence: Evidence,
    lineage: InternalLineage,
) -> str:
    """Resolve an in-corpus target or create an exact external N17 Repository stub."""
    normalized = normalize_github_repo_url(target_url)
    if not normalized:
        raise ValueError(f"Repository target URL is not a GitHub root: {target_url!r}")
    curated = resolve_repository_target(builder, normalized)
    if curated:
        return curated
    cache_key = (context.repo_id, normalized.casefold())
    cached = builder.external_repo_cache.get(cache_key)
    if cached:
        return cached
    full_name = urlparse(normalized).path.strip("/")
    owner, name = full_name.split("/", 1)
    node_id = f"github:repo-ref:{context.repo_id}:{stable_hash(normalized.casefold())}"
    emit_node(
        builder,
        make_node(
            node_id,
            "Repository",
            "A-C01",
            {
                "sourceRepoId": context.repo_id,
                "fullName": full_name,
                "htmlUrl": normalized,
                "owner": owner,
                "name": name,
            },
            normalized,
            "github_repository_url",
            REFERENCED,
            evidence,
            lineage,
        ),
    )
    referenced_identifier(
        context,
        builder,
        node_id,
        "Repository",
        "repo_url",
        target_url,
        normalized,
        evidence,
        lineage,
    )
    builder.external_repo_cache[cache_key] = node_id
    return node_id


def scalar_or_sorted_list(values: Iterable[Any]) -> Any:
    """Return one value or a deterministic list when declarations differ."""
    unique = sorted_unique(values)
    return unique[0] if len(unique) == 1 else unique


def internal_vcs_dependency(
    context: RepoContext,
    builder: GraphBuilder,
    dependency: JsonObject,
    dependency_index: int,
) -> None:
    """Create N5/E3 for a self-referencing VCS subpackage."""
    primary, declarations = select_primary_source(dependency["sources"])
    source_path = str(primary["manifest_path"])
    discriminator = (
        f"internal-vcs|{dependency['name']}|{dependency['subdirectory']}|{dependency['egg']}"
    )
    node_id = f"github:dependency:{context.repo_id}:{stable_hash(discriminator)}"
    component = dependency["subdirectory"] or dependency["egg"] or dependency["name"]
    attributes = {
        "sourceRepoId": context.repo_id,
        "name": dependency["name"],
        "dependencyKind": "internal_vcs_package",
        "ref": dependency["ref"],
        "subdirectory": dependency["subdirectory"],
        "egg": dependency["egg"],
        "ecosystem": dependency["ecosystem"],
        "depGroup": dependency["dep_group"],
        "raw": dependency["raw"],
        "sourceDeclarations": declarations,
    }
    evidence_text = primary.get("raw_line") or dependency["raw"] or dependency["name"]
    evidence = context.file_evidence(evidence_text, source_path)
    lineage = context.lineage(f"repo_dependencies[{dependency_index}]", source_path)
    emit_node(
        builder,
        make_node(
            node_id,
            "Dependency",
            "A-C03",
            attributes,
            f"internal-vcs:{context.repo_id}:{normalize_name(str(component))}",
            "internal_vcs_subpackage",
            CURATED,
            evidence,
            lineage,
        ),
    )
    builder.add_edge(
        "dependsOn",
        "C-C02",
        context.repo_node_id,
        node_id,
        {
            "raw": dependency["raw"],
            "depGroup": dependency["dep_group"],
            "ecosystem": dependency["ecosystem"],
            "sourceDeclarations": declarations,
            "dependencyKind": "internal_vcs_package",
        },
        evidence,
        lineage,
    )


def process_repository_dependencies(context: RepoContext, builder: GraphBuilder) -> None:
    """Resolve E10 targets and route monorepo self-references through N5/E3."""
    external_groups: dict[str, list[tuple[int, JsonObject, str]]] = defaultdict(list)
    source_key = github_repo_key(context.html_url)
    dependencies = sorted(context.repo["repo_dependencies"], key=stable_json)
    for sorted_index, dependency in enumerate(dependencies):
        normalized = normalize_github_repo_url(dependency["vcs_url"])
        primary, _ = select_primary_source(dependency["sources"])
        source_path = str(primary["manifest_path"])
        if not normalized:
            record_unresolved(
                builder,
                context,
                source_path,
                dependency["vcs_url"],
                "repository_target_url_unparseable",
            )
            continue
        if github_repo_key(normalized) == source_key:
            if dependency["subdirectory"] or dependency["egg"]:
                internal_vcs_dependency(context, builder, dependency, sorted_index)
            else:
                record_unresolved(
                    builder,
                    context,
                    source_path,
                    dependency["vcs_url"],
                    "self_vcs_reference_without_component",
                )
            continue
        external_groups[normalized.casefold()].append((sorted_index, dependency, normalized))
    for group_key in sorted(external_groups):
        group = external_groups[group_key]
        all_sources = [source for _, dependency, _ in group for source in dependency["sources"]]
        primary, declarations = select_primary_source(all_sources)
        source_path = str(primary["manifest_path"])
        evidence_text = primary.get("raw_line") or group[0][1]["raw"] or group[0][1]["name"]
        evidence = context.file_evidence(evidence_text, source_path)
        lineage = context.lineage("repo_dependencies", source_path)
        target = resolve_or_stub_repository(context, builder, group[0][2], evidence, lineage)
        dependency_declarations = sorted_unique(
            {
                "name": dependency["name"],
                "raw": dependency["raw"],
                "ref": dependency["ref"],
                "subdirectory": dependency["subdirectory"],
                "egg": dependency["egg"],
                "depGroup": dependency["dep_group"],
                "ecosystem": dependency["ecosystem"],
            }
            for _, dependency, _ in group
        )
        attributes = {
            "name": scalar_or_sorted_list(item["name"] for item in dependency_declarations),
            "raw": scalar_or_sorted_list(item["raw"] for item in dependency_declarations),
            "ref": scalar_or_sorted_list(item["ref"] for item in dependency_declarations),
            "subdirectory": scalar_or_sorted_list(item["subdirectory"] for item in dependency_declarations),
            "egg": scalar_or_sorted_list(item["egg"] for item in dependency_declarations),
            "depGroup": scalar_or_sorted_list(item["depGroup"] for item in dependency_declarations),
            "ecosystem": scalar_or_sorted_list(item["ecosystem"] for item in dependency_declarations),
            "sourceDeclarations": declarations,
            "dependencyDeclarations": dependency_declarations,
        }
        builder.add_edge(
            "dependsOnRepository",
            "C-C13",
            context.repo_node_id,
            target,
            attributes,
            evidence,
            lineage,
        )


def process_tool_implementations(context: RepoContext, builder: GraphBuilder) -> None:
    """Emit E8 default and exact structured implementation links."""
    for tool_record in context.tool_records:
        tool_id = str(tool_record["toolId"])
        tool_node = builder.nodes[tool_id]
        builder.add_edge(
            "implementedBy",
            "D-22",
            tool_id,
            context.repo_node_id,
            {
                "sourceType": tool_record["sourceType"],
                "softwareName": tool_record["softwareName"],
                "implementationBasis": "containing_repository",
            },
            tool_node.evidence,
            tool_node.internal_lineage,
        )
        targets: dict[str, list[tuple[str, str]]] = defaultdict(list)
        for key, raw_url in sorted(tool_record["urls"].items()):
            if not raw_url or normalized_url_key(key) not in IMPLEMENTATION_URL_KEYS:
                continue
            normalized = normalize_structured_repository_url(str(raw_url))
            if not normalized:
                record_deferred(
                    builder,
                    context,
                    tool_record["sourcePath"],
                    raw_url,
                    "structured_implementation_url_not_github_repository",
                )
                continue
            targets[normalized.casefold()].append((key, str(raw_url)))
        for target_key in sorted(targets):
            declarations = targets[target_key]
            normalized = normalize_structured_repository_url(declarations[0][1])
            if not normalized or github_repo_key(normalized) == github_repo_key(context.html_url):
                continue
            evidence = context.file_evidence(declarations[0][1], str(tool_record["sourcePath"]))
            lineage = context.lineage(
                f"structured_software_urls[{declarations[0][0]}]",
                str(tool_record["sourcePath"]),
            )
            target = resolve_or_stub_repository(context, builder, normalized, evidence, lineage)
            builder.add_edge(
                "implementedBy",
                "D-22",
                tool_id,
                target,
                {
                    "sourceType": tool_record["sourceType"],
                    "softwareName": tool_record["softwareName"],
                    "implementationBasis": "structured_repository_url",
                    "sourceKeys": sorted(key for key, _ in declarations),
                    "sourceUrls": sorted(url for _, url in declarations),
                },
                evidence,
                lineage,
            )


def citation_descriptor(citation: Mapping[str, Any]) -> str:
    """Build a stable concise descriptor for a structured CFF citation."""
    values = [citation.get("doi"), citation.get("title"), citation.get("journal"), citation.get("year")]
    descriptor = "; ".join(str(value) for value in values if value not in (None, ""))
    return descriptor or stable_json(dict(citation))


def seed_paper_reference(
    context: RepoContext,
    builder: GraphBuilder,
    citation: JsonObject,
    citation_role: str,
    citation_index: int,
    relation: str,
) -> str:
    """Create N15/E11-or-E12 plus DOI Identifier and N10/E13 authors."""
    doi = normalize_doi(citation["doi"])
    if not doi:
        raise ValueError("Paper citation requires a valid DOI")
    source_path = str(context.repo["citation"]["source_path"])
    node_id = (
        f"github:paper-ref:{context.repo_id}:"
        f"{stable_hash(f'{source_path}|{citation_role}|{citation_index}|{doi}')}"
    )
    descriptor = citation_descriptor(citation)
    evidence = context.file_evidence(descriptor, source_path)
    lineage = context.lineage(
        f"citation.{citation_role}" + (f"[{citation_index}]" if citation_role == "references" else ""),
        source_path,
    )
    emit_node(
        builder,
        make_node(
            node_id,
            "Paper",
            "A-P01",
            {
                "sourceRepoId": context.repo_id,
                "title": citation["title"],
                "type": citation["type"],
                "journal": citation["journal"],
                "year": citation["year"],
                "volume": citation["volume"],
                "number": citation["number"],
                "startPage": citation["start"],
                "endPage": citation["end"],
                "publisher": citation["publisher"],
                "url": citation["url"],
                "doi": citation["doi"],
            },
            f"doi:{doi}",
            "doi",
            REFERENCED,
            evidence,
            lineage,
        ),
    )
    referenced_identifier(
        context,
        builder,
        node_id,
        "Paper",
        "doi",
        str(citation["doi"]),
        doi,
        evidence,
        lineage,
    )
    builder.add_edge(
        relation,
        "C-C17",
        context.repo_node_id,
        node_id,
        {"citationRole": citation_role},
        evidence,
        lineage,
    )
    for author_index, author in enumerate(citation["authors"]):
        display_name = cff_author_display(author)
        orcid = normalize_orcid(author["orcid"])
        author_id = f"github:paper-author:{stable_hash(f'{node_id}|{author_index}')}"
        canonical_key = (
            f"orcid:{orcid}"
            if orcid
            else f"citation-name:{node_id}:{normalize_name(display_name)}"
        )
        author_lineage = context.lineage(
            f"citation.{citation_role}"
            + (f"[{citation_index}]" if citation_role == "references" else "")
            + f".authors[{author_index}]",
            source_path,
        )
        emit_node(
            builder,
            make_node(
                author_id,
                "Person",
                "A-AG01",
                {
                    "sourceRepoId": context.repo_id,
                    "familyNames": author["family_names"],
                    "givenNames": author["given_names"],
                    "displayName": display_name,
                    "orcid": author["orcid"],
                    "moduleRoleId": "A-P03",
                    "paperId": node_id,
                },
                canonical_key,
                "citation_orcid" if orcid else "citation_name",
                REFERENCED,
                evidence,
                author_lineage,
            ),
        )
        builder.add_edge(
            "hasAuthor",
            "C-P01",
            node_id,
            author_id,
            {"authorOrder": author_index + 1},
            evidence,
            author_lineage,
        )
    return node_id


def resolve_or_stub_dataset(
    context: RepoContext,
    builder: GraphBuilder,
    source_path: str,
    canonical_target_key: str,
    original_value: str,
    target_type: str,
    evidence: Evidence,
    lineage: InternalLineage,
) -> str:
    """Create a source-scoped N16 DatasetResource stub with an exact Identifier."""
    cache_key = (context.repo_id, source_path, canonical_target_key)
    cached = builder.dataset_cache.get(cache_key)
    if cached:
        return cached
    node_id = (
        f"github:dataset-ref:{context.repo_id}:"
        f"{stable_hash(f'{source_path}|{canonical_target_key}')}"
    )
    if canonical_target_key.startswith("hydroshare:"):
        id_type = "hydroshare_resource_id"
        normalized = canonical_target_key.split(":", 1)[1]
    else:
        id_type = "doi"
        normalized = canonical_target_key.split(":", 1)[1]
    emit_node(
        builder,
        make_node(
            node_id,
            "DatasetResource",
            "A-D01",
            {
                "sourceRepoId": context.repo_id,
                "targetType": target_type,
                "url": original_value if id_type == "hydroshare_resource_id" else None,
                "doi": original_value if id_type == "doi" else None,
                "resourceId": normalized if id_type == "hydroshare_resource_id" else None,
            },
            canonical_target_key,
            "hydroshare_resource_id" if id_type == "hydroshare_resource_id" else "doi",
            REFERENCED,
            evidence,
            lineage,
        ),
    )
    referenced_identifier(
        context,
        builder,
        node_id,
        "DatasetResource",
        id_type,
        original_value,
        normalized,
        evidence,
        lineage,
    )
    builder.dataset_cache[cache_key] = node_id
    return node_id


def process_cff_targets(context: RepoContext, builder: GraphBuilder) -> None:
    """Process valid structured CFF preferred citations and typed references."""
    citation = context.repo["citation"]
    if not (citation["present"] and citation["format"] == "cff") or citation["placeholder"]:
        return
    source_path = str(citation["source_path"])
    preferred = citation["preferred_citation"]
    preferred_has_value = any(
        preferred[key] not in (None, "", []) for key in preferred if key != "authors"
    ) or bool(preferred["authors"])
    if preferred_has_value:
        preferred_type = str(preferred["type"] or "").casefold()
        preferred_doi = normalize_doi(preferred["doi"])
        if preferred_doi and preferred_type in ARTICLE_LIKE_CFF_TYPES:
            seed_paper_reference(context, builder, preferred, "preferred_citation", 0, "referencePublication")
        elif preferred["doi"] and not preferred_doi:
            record_unresolved(
                builder,
                context,
                source_path,
                preferred["doi"],
                "invalid_doi_candidate",
            )
        else:
            record_deferred(
                builder,
                context,
                source_path,
                citation_descriptor(preferred),
                "preferred_citation_type_or_doi_insufficient",
            )
    for reference_index, reference in enumerate(citation["references"]):
        reference_type = str(reference["type"] or "").casefold()
        doi = normalize_doi(reference["doi"])
        if reference_type in ARTICLE_LIKE_CFF_TYPES and doi:
            seed_paper_reference(context, builder, reference, "references", reference_index, "citesPaper")
            continue
        if reference_type in DATASET_CFF_TYPES:
            evidence = context.file_evidence(citation_descriptor(reference), source_path)
            lineage = context.lineage(f"citation.references[{reference_index}]", source_path)
            resource_id = extract_hydroshare_resource_id(reference["url"])
            if resource_id:
                target = resolve_or_stub_dataset(
                    context,
                    builder,
                    source_path,
                    f"hydroshare:{resource_id}",
                    str(reference["url"]),
                    "dataset",
                    evidence,
                    lineage,
                )
            elif doi:
                target = resolve_or_stub_dataset(
                    context,
                    builder,
                    source_path,
                    f"doi:{doi}",
                    str(reference["doi"]),
                    "dataset",
                    evidence,
                    lineage,
                )
            else:
                record_unresolved(
                    builder,
                    context,
                    source_path,
                    citation_descriptor(reference),
                    "dataset_reference_identifier_unavailable",
                )
                continue
            builder.add_edge(
                "referencesDataset",
                "D-05",
                context.repo_node_id,
                target,
                {"citationRole": "reference", "referenceIndex": reference_index},
                evidence,
                lineage,
            )
            continue
        if reference_type in SOFTWARE_CFF_TYPES:
            record_deferred(
                builder,
                context,
                source_path,
                citation_descriptor(reference),
                "software_reference_relation_not_in_schema",
            )
            continue
        if reference["doi"] and not doi:
            record_unresolved(
                builder,
                context,
                source_path,
                reference["doi"],
                "invalid_doi_candidate",
            )
        else:
            record_deferred(
                builder,
                context,
                source_path,
                citation_descriptor(reference),
                "cff_reference_type_unknown",
            )


def process_readme_urls(context: RepoContext, builder: GraphBuilder) -> None:
    """Apply conservative README HydroShare, GitHub, DOI, and other URL rules."""
    readme = context.repo["readme"]
    urls = readme["deterministic_urls"]
    source_path = readme["source_path"]
    if not readme["present"] or not source_path:
        return
    source_path = str(source_path)
    for url in sorted(urls["hydroshare"]):
        resource_id = extract_hydroshare_resource_id(url)
        if not resource_id:
            record_unresolved(
                builder,
                context,
                source_path,
                url,
                "invalid_hydroshare_resource_url",
            )
            continue
        evidence = context.file_evidence(url, source_path)
        lineage = context.lineage("readme.deterministic_urls.hydroshare", source_path)
        target = resolve_or_stub_dataset(
            context,
            builder,
            source_path,
            f"hydroshare:{resource_id}",
            url,
            "dataset",
            evidence,
            lineage,
        )
        builder.add_edge(
            "referencesDataset",
            "D-05",
            context.repo_node_id,
            target,
            {"sourceType": "readme_url"},
            evidence,
            lineage,
        )
    source_repo_key = github_repo_key(context.html_url)
    for url in sorted(urls["github"]):
        classification = classify_github_url(url)
        target_key = github_repo_key(url)
        if classification == "repository_root" and target_key != source_repo_key:
            record_deferred(
                builder,
                context,
                source_path,
                url,
                "readme_github_url_semantics_unknown",
            )
        else:
            record_skipped(
                builder,
                context,
                source_path,
                url,
                f"readme_github_url_{classification}_no_relation",
            )
    typed_dois = {
        node.canonical_key.removeprefix("doi:")
        for node in builder.nodes.values()
        if node.class_name in {"Paper", "DatasetResource"} and node.canonical_key.startswith("doi:")
    }
    for candidate in sorted(urls["dois"]):
        doi = normalize_doi(candidate)
        if not doi:
            reason = (
                "doi_badge_or_image_rejected"
                if "badge" in candidate.casefold() or candidate.casefold().endswith(IMAGE_SUFFIXES)
                else "invalid_doi_candidate"
            )
            recorder = record_skipped if reason == "doi_badge_or_image_rejected" else record_unresolved
            recorder(builder, context, source_path, candidate, reason)
        elif doi in typed_dois:
            record_skipped(
                builder,
                context,
                source_path,
                candidate,
                "readme_doi_matches_structured_record",
            )
        else:
            record_deferred(
                builder,
                context,
                source_path,
                candidate,
                "readme_doi_type_unknown",
            )
    for url in sorted(urls["other"]):
        record_skipped(
            builder,
            context,
            source_path,
            url,
            "readme_other_url_not_mapped",
        )


def resolve_fork_parent(context: RepoContext, builder: GraphBuilder) -> str | None:
    """Resolve an exact non-null fork parent without inference."""
    parent = context.repo["fork_parent"]
    if parent is None:
        return None
    if isinstance(parent, int):
        return builder.repo_by_id.get(parent)
    if isinstance(parent, str):
        normalized = normalize_github_repo_url(parent)
        if not normalized and "/" in parent and not parent.startswith(("http://", "https://")):
            normalized = normalize_github_repo_url(f"https://github.com/{parent}")
        if normalized:
            evidence = context.metadata_evidence(parent)
            lineage = context.lineage("fork_parent", "repo_metadata.json:fork")
            return resolve_or_stub_repository(context, builder, normalized, evidence, lineage)
        return None
    if isinstance(parent, dict):
        if isinstance(parent.get("id"), int) and parent["id"] in builder.repo_by_id:
            return builder.repo_by_id[parent["id"]]
        candidate = parent.get("html_url") or parent.get("full_name")
        if candidate and not str(candidate).startswith(("http://", "https://")):
            candidate = f"https://github.com/{candidate}"
        normalized = normalize_github_repo_url(candidate)
        if normalized:
            evidence = context.metadata_evidence(parent)
            lineage = context.lineage("fork_parent", "repo_metadata.json:fork")
            return resolve_or_stub_repository(context, builder, normalized, evidence, lineage)
        return None
    return None


def process_repository_state_reports(context: RepoContext, builder: GraphBuilder) -> None:
    """Handle fork and archived-software dispositions without inference."""
    if context.repo["fork"]:
        parent = resolve_fork_parent(context, builder)
        if parent and parent != context.repo_node_id:
            builder.add_edge(
                "forkedFrom",
                "C-C14",
                context.repo_node_id,
                parent,
                {},
                context.metadata_evidence(context.repo["fork_parent"]),
                context.lineage("fork_parent", "repo_metadata.json:fork"),
            )
        else:
            record_unresolved(
                builder,
                context,
                "repo_metadata.json:fork",
                context.repo["fork_parent"],
                "fork_parent_unavailable",
            )
    doi_disposition = build_archive_doi_disposition(context.repo)
    archive_candidates = list(doi_disposition.eligible_archive_candidates)
    if archive_candidates:
        record_deferred(
            builder,
            context,
            "identifiers",
            archive_candidates,
            "archived_as_requires_cross_module_identifier_match",
        )


def run_pass2(contexts: Sequence[RepoContext], builder: GraphBuilder) -> None:
    """Emit relations, resolve exact targets, and complete report dispositions."""
    for context in contexts:
        emit_repository_internal_edges(context, builder)
        process_repository_dependencies(context, builder)
        process_tool_implementations(context, builder)
        process_cff_targets(context, builder)
        process_readme_urls(context, builder)
        process_repository_state_reports(context, builder)


def report_sort_key(record: Mapping[str, Any]) -> tuple[int, str, str, str, str]:
    """Return the deterministic ordering key for extraction report records."""
    return (
        int(record.get("repoId") or 0),
        str(record.get("category") or ""),
        str(record.get("sourcePath") or ""),
        str(record.get("reason") or ""),
        stable_json(record.get("value")),
    )


def build_stats(
    corpus: JsonObject,
    nodes: Sequence[JsonObject],
    edges: Sequence[JsonObject],
    reports: Mapping[str, Sequence[JsonObject]],
) -> JsonObject:
    """Build deterministic structural and extraction counters for the output."""
    node_counts = Counter(str(node["class"]) for node in nodes)
    edge_counts = Counter(str(edge["relation"]) for edge in edges)
    curated_count = sum(node["curationStatus"] == CURATED for node in nodes)
    referenced_count = sum(node["curationStatus"] == REFERENCED for node in nodes)
    file_nodes = [node for node in nodes if node["class"] == "File"]
    phase_a_warning_count = sum(
        len(repo["provenance"]["parse_warnings"]) for repo in corpus["repos"]
    )
    return {
        "inputRepositoryCount": len(corpus["repos"]),
        "inputFileInventoryRecordCount": sum(
            len(repo["files"]["inventory"]) for repo in corpus["repos"]
        ),
        "inputDownloadedFileRecordCount": sum(
            repo["files"]["downloaded_count"] for repo in corpus["repos"]
        ),
        "inputPackageDependencyCount": sum(
            len(repo["dependencies"]) for repo in corpus["repos"]
        ),
        "inputRepositoryDependencyCount": sum(
            len(repo["repo_dependencies"]) for repo in corpus["repos"]
        ),
        "inputExecutionEnvironmentCount": sum(
            len(repo["execution_environment"]) for repo in corpus["repos"]
        ),
        "nodeCount": len(nodes),
        "edgeCount": len(edges),
        "nodesByClass": dict(sorted(node_counts.items())),
        "edgesByRelation": dict(sorted(edge_counts.items())),
        "curatedNodeCount": curated_count,
        "referencedNodeCount": referenced_count,
        "fileNodeCount": len(file_nodes),
        "downloadedFileNodeCount": sum(node["attributes"]["downloaded"] for node in file_nodes),
        "nonDownloadedFileNodeCount": sum(not node["attributes"]["downloaded"] for node in file_nodes),
        "packageDependencyNodeCount": sum(
            node["class"] == "Dependency"
            and node["identityRegime"] == "ecosystem_package_name"
            for node in nodes
        ),
        "internalVcsDependencyNodeCount": sum(
            node["class"] == "Dependency"
            and node["identityRegime"] == "internal_vcs_subpackage"
            for node in nodes
        ),
        "executionEnvironmentNodeCount": node_counts["ExecutionEnvironment"],
        "contributorPersonNodeCount": sum(
            node["class"] == "Person"
            and node["attributes"].get("moduleRoleId") == "A-C05"
            for node in nodes
        ),
        "paperNodeCount": node_counts["Paper"],
        "datasetStubCount": sum(
            node["class"] == "DatasetResource" and node["curationStatus"] == REFERENCED
            for node in nodes
        ),
        "repositoryStubCount": sum(
            node["class"] == "Repository" and node["curationStatus"] == REFERENCED
            for node in nodes
        ),
        "toolNodeCount": node_counts["Tool"],
        "modelVersionNodeCount": node_counts["ModelVersion"],
        "manifestClassificationCount": sum(
            len(repo["provenance"]["manifest_classifications"]) for repo in corpus["repos"]
        ),
        "deferredCount": len(reports["deferred"]),
        "skippedCount": len(reports["skipped"]),
        "unresolvedCount": len(reports["unresolved"]),
        "warningCount": len(reports["warnings"]),
        "phaseAWarningCount": phase_a_warning_count,
    }


def build_output(corpus: JsonObject, builder: GraphBuilder) -> JsonObject:
    """Assemble sorted graph, report arrays, versions, and deterministic stats."""
    nodes = [builder.nodes[node_id].to_dict() for node_id in sorted(builder.nodes)]
    edges = [builder.edges[edge_id].to_dict() for edge_id in sorted(builder.edges)]
    reports = {
        report_type: sorted(records.values(), key=report_sort_key)
        for report_type, records in builder.reports.items()
    }
    stats = build_stats(corpus, nodes, edges, reports)
    return {
        "schema_version": OUTPUT_SCHEMA_VERSION,
        "phase_b_version": PHASE_B_VERSION,
        "source_schema_version": corpus["schema_version"],
        "source_type": SOURCE_TYPE,
        "nodes": nodes,
        "edges": edges,
        "deferred": reports["deferred"],
        "skipped": reports["skipped"],
        "unresolved": reports["unresolved"],
        "warnings": reports["warnings"],
        "stats": stats,
    }


def _validate_public_evidence(
    evidence: Any,
    owner_label: str,
    issues: list[str],
) -> None:
    """Validate required public evidence fields and reject local/internal locations."""
    if not isinstance(evidence, dict):
        issues.append(f"{owner_label}: evidence is not an object")
        return
    missing = EVIDENCE_REQUIRED_KEYS - set(evidence)
    if missing:
        issues.append(f"{owner_label}: evidence missing keys {sorted(missing)}")
        return
    for key in ("evidenceText", "sourceLocation", "extractionMethod", "sourceArtifact"):
        if not nonempty_text(evidence.get(key)):
            issues.append(f"{owner_label}: evidence.{key} is empty")
    location = str(evidence.get("sourceLocation") or "")
    if not location.startswith(("https://", "http://")):
        issues.append(f"{owner_label}: sourceLocation is not public HTTP(S): {location}")
    lowered = location.casefold()
    if any(raw_name in lowered for raw_name in LOCAL_SOURCE_NAMES):
        issues.append(f"{owner_label}: sourceLocation exposes internal raw filename: {location}")
    if location.startswith(("/", "file://")) or re.match(r"^[A-Za-z]:[\\/]", location):
        issues.append(f"{owner_label}: sourceLocation is a local filesystem path: {location}")
    if "/data/raw/" in lowered or "/data/interim/" in lowered:
        issues.append(f"{owner_label}: sourceLocation exposes a local corpus path: {location}")
    if evidence.get("version") in (None, ""):
        issues.append(f"{owner_label}: evidence.version is empty")


def _validate_lineage(lineage: Any, owner_label: str, issues: list[str]) -> None:
    """Validate the minimal internal-lineage shape."""
    if not isinstance(lineage, dict):
        issues.append(f"{owner_label}: internalLineage is not an object")
        return
    if not lineage.get("phaseAField") or not lineage.get("phaseAVersion"):
        issues.append(f"{owner_label}: internalLineage lacks phaseAField/phaseAVersion")


def _validate_set_like_arrays(record: Any, location: str, issues: list[str]) -> None:
    """Validate deterministic ordering for known set-like arrays recursively."""
    set_like_keys = {
        "topics",
        "extras",
        "manifestScopes",
        "sourceKeys",
        "sourceUrls",
        "keywords",
        "channels",
        "metricExclusion",
        "dependencyDeclarations",
    }
    if isinstance(record, dict):
        for key, value in record.items():
            if key == "sourceDeclarations" and isinstance(value, list):
                if value != sorted(value, key=source_sort_key):
                    issues.append(f"{location}.{key} is not in primary-evidence order")
            elif key in set_like_keys and isinstance(value, list):
                if value != sorted_unique(value):
                    issues.append(f"{location}.{key} is not deterministically sorted")
            _validate_set_like_arrays(value, f"{location}.{key}", issues)
    elif isinstance(record, list):
        for index, value in enumerate(record):
            _validate_set_like_arrays(value, f"{location}[{index}]", issues)


def _expected_repo_node_id(repo: Mapping[str, Any]) -> str:
    """Return the expected curated repository node ID."""
    return f"github:repo:{repo['repo_id']}"


def _expected_file_node_id(repo: Mapping[str, Any], file_entry: Mapping[str, Any]) -> str:
    """Return the expected source-scoped File node ID."""
    return f"github:file:{repo['repo_id']}:{stable_hash(str(file_entry['path']))}"


def _expected_environment_node_id(repo: Mapping[str, Any], environment: Mapping[str, Any]) -> str:
    """Return the expected source-scoped environment node ID."""
    discriminator = f"{environment['kind']}|{environment['source_path']}"
    return f"github:env:{repo['repo_id']}:{stable_hash(discriminator)}"


def _expected_package_dependency_id(repo: Mapping[str, Any], dependency: Mapping[str, Any]) -> str:
    """Return the expected source-scoped package dependency node ID."""
    ecosystem = str(dependency["ecosystem"] or "unknown").casefold()
    canonical_name = canonicalize_package_name(dependency["name"], ecosystem)
    return f"github:dependency:{repo['repo_id']}:{stable_hash(f'{ecosystem}|{canonical_name}')}"


def validate_output(output: JsonObject, corpus: JsonObject) -> list[str]:
    """Validate structural, semantic, provenance, coverage, and count requirements."""
    issues: list[str] = []
    try:
        validate_input_field_accounting(corpus)
    except ValueError as exc:
        issues.append(str(exc))
    expected_top = {
        "schema_version",
        "phase_b_version",
        "source_schema_version",
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
        issues.append(f"output top-level keys differ: {sorted(set(output) ^ expected_top)}")
    if output.get("schema_version") != OUTPUT_SCHEMA_VERSION:
        issues.append("unsupported output schema version")
    if output.get("phase_b_version") != PHASE_B_VERSION:
        issues.append("unexpected phase_b_version")
    if output.get("source_schema_version") != corpus.get("schema_version"):
        issues.append("source_schema_version does not match input")
    nodes = output.get("nodes") if isinstance(output.get("nodes"), list) else []
    edges = output.get("edges") if isinstance(output.get("edges"), list) else []
    if [node.get("id") for node in nodes] != sorted(node.get("id") for node in nodes):
        issues.append("nodes are not sorted by id")
    if [edge.get("id") for edge in edges] != sorted(edge.get("id") for edge in edges):
        issues.append("edges are not sorted by id")
    node_ids = [node.get("id") for node in nodes]
    edge_ids = [edge.get("id") for edge in edges]
    if len(node_ids) != len(set(node_ids)):
        issues.append("duplicate node IDs")
    if len(edge_ids) != len(set(edge_ids)):
        issues.append("duplicate edge IDs")
    node_by_id = {str(node.get("id")): node for node in nodes}
    edge_by_id = {str(edge.get("id")): edge for edge in edges}
    allowed_node_pairs = {
        ("Repository", "A-C01"),
        ("Identifier", "A-ID01"),
        ("File", "A-C02"),
        ("Dependency", "A-C03"),
        ("ExecutionEnvironment", "A-C04"),
        ("Person", "A-AG01"),
        ("Organization", "A-AG02"),
        ("License", "A-C06"),
        ("Tool", "A-DOM02"),
        ("ModelVersion", "A-C10"),
        ("Paper", "A-P01"),
        ("DatasetResource", "A-D01"),
    }
    allowed_relation_ids = {
        "hasIdentifier": {"C-C06", "C-P04", "C-D04"},
        "hasFile": {"C-C01"},
        "dependsOn": {"C-C02"},
        "hasExecutionEnvironment": {"C-C03"},
        "hasContributor": {"C-C04"},
        "affiliatedWith": {"A-AG-R1"},
        "hasLicense": {"C-C05"},
        "implementedBy": {"D-22"},
        "hasModelVersion": {"C-C09"},
        "dependsOnRepository": {"C-C13"},
        "referencePublication": {"C-C17"},
        "citesPaper": {"C-C17"},
        "hasAuthor": {"C-P01"},
        "referencesDataset": {"D-05"},
        "forkedFrom": {"C-C14"},
    }
    license_semantic_groups: dict[tuple[Any, str, str], list[str]] = defaultdict(list)
    malformed_license_markers = ("{'text':", "{'file':", '{"text":', '{"file":')
    for node in nodes:
        label = f"node {node.get('id')}"
        missing = NODE_REQUIRED_KEYS - set(node)
        if missing:
            issues.append(f"{label}: missing keys {sorted(missing)}")
            continue
        if (node["class"], node["inventoryId"]) not in allowed_node_pairs:
            issues.append(f"{label}: undeclared class/inventory pair")
        if node["curationStatus"] not in {CURATED, REFERENCED}:
            issues.append(f"{label}: invalid curationStatus {node['curationStatus']!r}")
        if not node["canonicalKey"] or not node["identityRegime"]:
            issues.append(f"{label}: canonicalKey/identityRegime is empty")
        _validate_public_evidence(node["evidence"], label, issues)
        _validate_lineage(node["internalLineage"], label, issues)
        _validate_set_like_arrays(node, label, issues)
        if node["class"] == "License":
            declaration = str(node["attributes"].get("declaration") or "")
            name = str(node["attributes"].get("name") or "")
            canonical_key = str(node["canonicalKey"])
            semantic_fields = (declaration.casefold(), name.casefold(), canonical_key.casefold())
            if any(marker in field for field in semantic_fields for marker in malformed_license_markers):
                issues.append(f"{label}: malformed Python-dictionary license representation")
            if not declaration.strip():
                issues.append(f"{label}: empty License declaration")
            if node["attributes"].get("declarationKind") == "file":
                issues.append(f"{label}: file pointer was emitted as a License identity")
            if node["attributes"].get("sourceType") == "software_metadata":
                disposition = normalize_software_license_declaration(
                    node["attributes"].get("originalValue")
                )
                if not disposition.is_text_declaration:
                    issues.append(f"{label}: non-text software license produced a License node")
            semantic_declaration = " ".join(declaration.split()).casefold()
            group_key = (
                node["attributes"].get("sourceRepoId"),
                str(node["attributes"].get("declarationScope") or ""),
                semantic_declaration,
            )
            license_semantic_groups[group_key].append(node["id"])
    for group_key, grouped_node_ids in sorted(license_semantic_groups.items(), key=lambda item: stable_json(item[0])):
        if len(grouped_node_ids) > 1:
            issues.append(
                "semantically equivalent License declarations duplicated within scope "
                f"{group_key}: {sorted(grouped_node_ids)}"
            )
    edge_triples: set[tuple[str, str, str]] = set()
    for edge in edges:
        label = f"edge {edge.get('id')}"
        missing = EDGE_REQUIRED_KEYS - set(edge)
        if missing:
            issues.append(f"{label}: missing keys {sorted(missing)}")
            continue
        if edge["source"] not in node_by_id or edge["target"] not in node_by_id:
            issues.append(f"{label}: endpoint missing from nodes")
        if edge["relation"] not in allowed_relation_ids or edge["inventoryId"] not in allowed_relation_ids[edge["relation"]]:
            issues.append(f"{label}: undeclared relation/inventory pair")
        triple = (edge["source"], edge["relation"], edge["target"])
        if triple in edge_triples:
            issues.append(f"{label}: duplicate semantic edge")
        edge_triples.add(triple)
        _validate_public_evidence(edge["evidence"], label, issues)
        _validate_lineage(edge["internalLineage"], label, issues)
        _validate_set_like_arrays(edge, label, issues)
    if any(edge.get("relation") == "dependsOnRepository" and edge.get("source") == edge.get("target") for edge in edges):
        issues.append("dependsOnRepository self-loop detected")
    if any(edge.get("relation") == "referencesRepository" for edge in edges):
        issues.append("README or another source emitted undeclared referencesRepository")
    expected_repo_ids = {_expected_repo_node_id(repo) for repo in corpus["repos"]}
    actual_curated_repo_ids = {
        node["id"]
        for node in nodes
        if node["class"] == "Repository" and node["curationStatus"] == CURATED
    }
    if actual_curated_repo_ids != expected_repo_ids:
        issues.append("curated Repository nodes do not match Phase A repositories")
    expected_file_ids: set[str] = set()
    expected_has_file_edges: set[str] = set()
    expected_downloaded_count = 0
    expected_environment_ids: set[str] = set()
    expected_dependency_ids: set[str] = set()
    api_versions: dict[str, int | float] = {}
    for repo in corpus["repos"]:
        repo_node_id = _expected_repo_node_id(repo)
        full_name = str(repo["full_name"])
        epoch = repo["archive"]["downloaded_at_epoch"]
        api_versions[build_api_url(full_name)] = epoch
        api_versions[build_api_url(full_name, contributors=True)] = epoch
        sha = str(repo["archive"]["frozen_commit_sha"])
        html_url = str(repo["html_url"])
        repo_file_ids: set[str] = set()
        for file_entry in repo["files"]["inventory"]:
            file_id = _expected_file_node_id(repo, file_entry)
            expected_file_ids.add(file_id)
            repo_file_ids.add(file_id)
            expected_has_file_edges.add(make_edge_id(repo_node_id, "hasFile", file_id))
            if file_entry["downloaded"]:
                expected_downloaded_count += 1
            node = node_by_id.get(file_id)
            if node:
                expected_location = build_blob_url(html_url, sha, str(file_entry["path"]))
                if node["evidence"]["sourceLocation"] != expected_location:
                    issues.append(f"{file_id}: File evidence URL does not match SHA-pinned path")
                if node["attributes"].get("downloaded") != file_entry["downloaded"]:
                    issues.append(f"{file_id}: downloaded flag mismatch")
                if node["attributes"].get("contentAvailable") != file_entry["downloaded"]:
                    issues.append(f"{file_id}: contentAvailable mismatch")
        if len(repo_file_ids) != repo["files"]["total_count"]:
            issues.append(f"{repo['name']}: input inventory IDs are not unique")
        for dependency in repo["dependencies"]:
            expected_dependency_ids.add(_expected_package_dependency_id(repo, dependency))
        for environment in repo["execution_environment"]:
            env_id = _expected_environment_node_id(repo, environment)
            expected_environment_ids.add(env_id)
            env_node = node_by_id.get(env_id)
            if env_node:
                expected_location = build_blob_url(html_url, sha, str(environment["source_path"]))
                if env_node["evidence"]["sourceLocation"] != expected_location:
                    issues.append(f"{env_id}: environment provenance is not source-file based")
        for contributor in repo["contributors"]:
            source_path = str(contributor["source_path"])
            login = str(contributor["login"] or "")
            bot_id = (
                f"github:person:{repo['repo_id']}:"
                f"{stable_hash(f'github|{source_path}|{contributor['github_id']}|{login}')}"
            )
            if contributor["is_bot"] and bot_id in node_by_id:
                issues.append(f"{repo['name']}: bot contributor produced Person node")
        for software_index, software in enumerate(repo["software_metadata"]):
            disposition = normalize_software_license_declaration(software["license"])
            phase_a_field = f"software_metadata[{software_index}].license"
            matching_license_nodes = [
                node
                for node in nodes
                if node["class"] == "License"
                and node["attributes"].get("sourceRepoId") == repo["repo_id"]
                and node["attributes"].get("sourceType") == "software_metadata"
                and any(
                    declaration.get("phaseAField") == phase_a_field
                    for declaration in node["attributes"].get("sourceDeclarations", [])
                )
            ]
            if disposition.is_text_declaration:
                normalized_text = " ".join(str(disposition.normalized_value).split()).casefold()
                if len(matching_license_nodes) != 1 or " ".join(
                    str(matching_license_nodes[0]["attributes"].get("declaration") or "").split()
                ).casefold() != normalized_text:
                    issues.append(
                        f"{repo['name']}: structured text license was not emitted exactly once: "
                        f"{phase_a_field}"
                    )
            elif matching_license_nodes:
                issues.append(
                    f"{repo['name']}: non-text structured license produced License node(s): "
                    f"{phase_a_field}"
                )
            if disposition.kind == "file" and not any(
                record["repoId"] == repo["repo_id"]
                and record["sourcePath"] == software["source_path"]
                and record["reason"] == "license_file_reference_requires_content_resolution"
                and record["value"] == disposition.normalized_value
                for record in output.get("deferred", [])
            ):
                issues.append(f"{repo['name']}: license file pointer lacks deferred record: {phase_a_field}")
            if disposition.kind == "empty_text" and not any(
                record["repoId"] == repo["repo_id"]
                and record["sourcePath"] == software["source_path"]
                and record["reason"] == "empty_structured_license_text"
                and stable_json(record["value"]) == stable_json(disposition.original_value)
                for record in output.get("skipped", [])
            ):
                issues.append(f"{repo['name']}: empty structured license lacks skipped record: {phase_a_field}")
            if disposition.kind == "unsupported" and not any(
                record["repoId"] == repo["repo_id"]
                and record["sourcePath"] == software["source_path"]
                and record["reason"] == "unsupported_structured_license_mapping"
                and stable_json(record["value"]) == stable_json(disposition.original_value)
                for record in output.get("deferred", [])
            ):
                issues.append(f"{repo['name']}: unsupported license mapping lacks deferred record: {phase_a_field}")
        citation = repo["citation"]
        expected_affiliation_edge_ids: set[str] = set()
        if citation["present"] and citation["format"] == "cff" and not citation["placeholder"]:
            source_path = str(citation["source_path"])
            expected_affiliation_location = build_blob_url(
                str(repo["html_url"]),
                str(repo["archive"]["frozen_commit_sha"]),
                source_path,
            )
            for author_index, author in enumerate(citation["software_authors"]):
                affiliation = str(author["affiliation"] or "").strip()
                if not affiliation:
                    continue
                person_id = (
                    f"github:person:{repo['repo_id']}:"
                    f"{stable_hash(f'cff-software-author|{source_path}|{author_index}')}"
                )
                organization_id = (
                    f"github:organization:{repo['repo_id']}:"
                    f"{stable_hash(f'{source_path}|{affiliation}')}"
                )
                expected_edge_id = make_edge_id(person_id, "affiliatedWith", organization_id)
                expected_affiliation_edge_ids.add(expected_edge_id)
                affiliation_edge = edge_by_id.get(expected_edge_id)
                expected_phase_a_field = f"citation.software_authors[{author_index}].affiliation"
                if affiliation_edge is None:
                    issues.append(f"{repo['name']}: missing affiliatedWith edge for author {author_index}")
                    continue
                if affiliation_edge["source"] != person_id or affiliation_edge["target"] != organization_id:
                    issues.append(f"{repo['name']}: affiliatedWith endpoints mismatch for author {author_index}")
                if affiliation_edge["internalLineage"].get("phaseAField") != expected_phase_a_field:
                    issues.append(
                        f"{repo['name']}: affiliatedWith lineage mismatch for author {author_index}: "
                        f"{affiliation_edge['internalLineage'].get('phaseAField')!r}"
                    )
                if affiliation_edge["evidence"].get("sourceLocation") != expected_affiliation_location:
                    issues.append(f"{repo['name']}: affiliatedWith public evidence mismatch for author {author_index}")
        actual_affiliation_edge_ids = {
            edge["id"]
            for edge in edges
            if edge["relation"] == "affiliatedWith"
            and node_by_id.get(edge["source"], {}).get("attributes", {}).get("sourceRepoId")
            == repo["repo_id"]
        }
        if actual_affiliation_edge_ids != expected_affiliation_edge_ids:
            issues.append(f"{repo['name']}: affiliatedWith edge set does not match CFF authors")
        doi_disposition = build_archive_doi_disposition(repo)
        archive_candidates = list(doi_disposition.eligible_archive_candidates)
        archive_reports = [
            record
            for record in output.get("deferred", [])
            if record["repoId"] == repo["repo_id"]
            and record["reason"] == "archived_as_requires_cross_module_identifier_match"
        ]
        for archive_report in archive_reports:
            report_values = archive_report.get("value")
            if not isinstance(report_values, list):
                continue
            for candidate in report_values:
                normalized_candidate = normalize_doi(str(candidate))
                if not normalized_candidate:
                    continue
                contexts = doi_disposition.contexts_for(normalized_candidate)
                if contexts:
                    issues.append(
                        "archivedAs candidate already has structured typing: "
                        f"repoId={repo['repo_id']}, repoName={repo['name']!r}, "
                        f"DOI={normalized_candidate!r}, structured typing context={list(contexts)!r}"
                    )
        if archive_candidates:
            if len(archive_reports) != 1 or archive_reports[0]["value"] != archive_candidates:
                issues.append(f"{repo['name']}: archivedAs deferred candidates mismatch normalized DOI identifiers")
        elif archive_reports:
            issues.append(f"{repo['name']}: empty archivedAs deferred record emitted without identifier")
        source_repo_key = github_repo_key(str(repo["html_url"]))
        for dependency in repo["repo_dependencies"]:
            normalized_target = normalize_github_repo_url(dependency["vcs_url"])
            primary, _ = select_primary_source(dependency["sources"])
            if not normalized_target:
                if not any(
                    record["repoId"] == repo["repo_id"]
                    and record["reason"] == "repository_target_url_unparseable"
                    for record in output.get("unresolved", [])
                ):
                    issues.append(f"{repo['name']}: unparseable VCS target lacks unresolved record")
                continue
            if github_repo_key(normalized_target) == source_repo_key:
                if dependency["subdirectory"] or dependency["egg"]:
                    discriminator = (
                        f"internal-vcs|{dependency['name']}|{dependency['subdirectory']}|{dependency['egg']}"
                    )
                    expected_internal_id = (
                        f"github:dependency:{repo['repo_id']}:{stable_hash(discriminator)}"
                    )
                    if expected_internal_id not in node_by_id or not any(
                        edge["relation"] == "dependsOn"
                        and edge["source"] == repo_node_id
                        and edge["target"] == expected_internal_id
                        for edge in edges
                    ):
                        issues.append(f"{repo['name']}: self VCS component was not routed to Dependency")
                elif not any(
                    record["repoId"] == repo["repo_id"]
                    and record["reason"] == "self_vcs_reference_without_component"
                    for record in output.get("unresolved", [])
                ):
                    issues.append(f"{repo['name']}: uninformative self VCS reference lacks unresolved record")
                continue
            curated_target = next(
                (
                    node["id"]
                    for node in nodes
                    if node["class"] == "Repository"
                    and (
                        (
                            node["curationStatus"] == REFERENCED
                            and node["canonicalKey"].casefold() == normalized_target.casefold()
                        )
                        or (
                            node["curationStatus"] == CURATED
                            and str(
                                normalize_github_repo_url(node["attributes"].get("htmlUrl")) or ""
                            ).casefold()
                            == normalized_target.casefold()
                        )
                    )
                ),
                None,
            )
            if curated_target is None or not any(
                edge["relation"] == "dependsOnRepository"
                and edge["source"] == repo_node_id
                and edge["target"] == curated_target
                for edge in edges
            ):
                issues.append(
                    f"{repo['name']}: external VCS target did not resolve or become a referenced stub: "
                    f"{normalized_target} ({primary['manifest_path']})"
                )
        if citation["placeholder"]:
            for node in nodes:
                lineage_field = str(node.get("internalLineage", {}).get("phaseAField") or "")
                if node.get("class") in {"Person", "Organization", "Tool", "License", "ModelVersion", "Paper"} and lineage_field.startswith("citation") and node.get("attributes", {}).get("sourceRepoId") == repo["repo_id"]:
                    issues.append(f"{repo['name']}: placeholder CFF produced forbidden {node['class']} node")
    actual_file_ids = {node["id"] for node in nodes if node["class"] == "File"}
    if actual_file_ids != expected_file_ids:
        issues.append("File nodes do not exactly match files.inventory entries")
    actual_has_file_edges = {edge["id"] for edge in edges if edge["relation"] == "hasFile"}
    if actual_has_file_edges != expected_has_file_edges:
        issues.append("hasFile edges do not exactly match files.inventory entries")
    actual_downloaded_count = sum(
        bool(node["attributes"].get("downloaded")) for node in nodes if node["class"] == "File"
    )
    if actual_downloaded_count != expected_downloaded_count:
        issues.append("downloaded File node total does not match Phase A")
    actual_package_dependency_ids = {
        node["id"]
        for node in nodes
        if node["class"] == "Dependency" and node["identityRegime"] == "ecosystem_package_name"
    }
    if actual_package_dependency_ids != expected_dependency_ids:
        issues.append("package Dependency mentions do not exactly match Phase A dependencies")
    actual_environment_ids = {node["id"] for node in nodes if node["class"] == "ExecutionEnvironment"}
    if actual_environment_ids != expected_environment_ids:
        issues.append("ExecutionEnvironment nodes do not exactly match Phase A records")
    for node in nodes:
        location = str(node["evidence"]["sourceLocation"])
        if location in api_versions and node["evidence"]["version"] != api_versions[location]:
            issues.append(f"{node['id']}: API evidence version is not acquisition epoch")
        if node["class"] == "Paper" and normalize_doi(node["canonicalKey"].removeprefix("doi:")) is None:
            issues.append(f"{node['id']}: Paper lacks valid DOI canonical key")
        if node["class"] == "DatasetResource" and node["canonicalKey"].startswith("hydroshare:"):
            resource_id = node["canonicalKey"].split(":", 1)[1]
            if not re.fullmatch(r"[0-9a-f]{32}", resource_id):
                issues.append(f"{node['id']}: invalid HydroShare resource identifier")
    paper_author_ids = {
        node["id"]
        for node in nodes
        if node["class"] == "Person" and node["attributes"].get("moduleRoleId") == "A-P03"
    }
    for author_id in paper_author_ids:
        if not any(edge["relation"] == "hasAuthor" and edge["target"] == author_id for edge in edges):
            issues.append(f"{author_id}: paper author lacks hasAuthor edge")
        if any(edge["relation"] == "hasContributor" and edge["target"] == author_id for edge in edges):
            issues.append(f"{author_id}: paper author incorrectly attached to Repository")
    for edge in edges:
        location = str(edge["evidence"]["sourceLocation"])
        if location in api_versions and edge["evidence"]["version"] != api_versions[location]:
            issues.append(f"{edge['id']}: API edge evidence version is not acquisition epoch")
    for report_type in ("deferred", "skipped", "unresolved", "warnings"):
        records = output.get(report_type) if isinstance(output.get(report_type), list) else []
        if records != sorted(records, key=report_sort_key):
            issues.append(f"{report_type} report is not deterministically sorted")
    for record in output.get("deferred", []):
        if record.get("reason") != "archived_as_requires_cross_module_identifier_match":
            continue
        value = record.get("value")
        if not isinstance(value, list) or not value:
            issues.append(
                "archived_as_requires_cross_module_identifier_match has empty identifier value: "
                f"repo={record.get('repoName')!r}"
            )
            continue
        normalized_candidates = sorted(
            {normalized for candidate in value if (normalized := normalize_doi(str(candidate)))}
        )
        if value != normalized_candidates:
            issues.append(
                "archived_as_requires_cross_module_identifier_match contains invalid or "
                f"non-normalized identifiers: repo={record.get('repoName')!r}, value={value!r}"
            )
    expected_stats = build_stats(
        corpus,
        nodes,
        edges,
        {key: output.get(key, []) for key in ("deferred", "skipped", "unresolved", "warnings")},
    )
    if output.get("stats") != expected_stats:
        issues.append("stats do not match output records")
    return issues


class OutputValidationError(ValueError):
    """Raised when Phase B output fails one or more contract validations."""

    def __init__(self, issues: Sequence[str]) -> None:
        """Store actionable issues and build a concise exception message."""
        self.issues = list(issues)
        super().__init__("Phase B output validation failed:\n- " + "\n- ".join(self.issues))


def extract_corpus(corpus: JsonObject) -> JsonObject:
    """Run the complete two-pass deterministic GitHub extraction."""
    validate_input_field_accounting(corpus)
    builder = GraphBuilder()
    contexts = build_contexts(corpus, builder)
    run_pass2(contexts, builder)
    output = build_output(corpus, builder)
    issues = validate_output(output, corpus)
    if issues:
        raise OutputValidationError(issues)
    return output


def write_output(output: JsonObject, output_path: Path) -> None:
    """Write byte-stable UTF-8 JSON with a final newline."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(output, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def reason_frequencies(records: Sequence[Mapping[str, Any]]) -> dict[str, int]:
    """Count deterministic report reasons."""
    return dict(sorted(Counter(str(record["reason"]) for record in records).items()))


def print_report(output: JsonObject) -> None:
    """Print the complete deterministic extraction and validation summary."""
    stats = output["stats"]
    print("GitHub Phase B validation report")
    print(f"schema_version: {output['schema_version']}")
    print(f"phase_b_version: {output['phase_b_version']}")
    print(f"source_schema_version: {output['source_schema_version']}")
    print(f"input repositories: {stats['inputRepositoryCount']}")
    print(f"input file inventory records: {stats['inputFileInventoryRecordCount']}")
    print(f"input downloaded file records: {stats['inputDownloadedFileRecordCount']}")
    print(f"input package dependencies: {stats['inputPackageDependencyCount']}")
    print(f"input repository dependencies: {stats['inputRepositoryDependencyCount']}")
    print(f"input execution environments: {stats['inputExecutionEnvironmentCount']}")
    print(f"nodes: {stats['nodeCount']}")
    print(f"edges: {stats['edgeCount']}")
    print(f"nodes by class: {json.dumps(stats['nodesByClass'], sort_keys=True)}")
    print(f"edges by relation: {json.dumps(stats['edgesByRelation'], sort_keys=True)}")
    print(f"curated nodes: {stats['curatedNodeCount']}")
    print(f"referenced nodes: {stats['referencedNodeCount']}")
    print(f"file nodes: {stats['fileNodeCount']}")
    print(f"downloaded file nodes: {stats['downloadedFileNodeCount']}")
    print(f"non-downloaded file nodes: {stats['nonDownloadedFileNodeCount']}")
    print(f"deferred: {stats['deferredCount']} {json.dumps(reason_frequencies(output['deferred']), sort_keys=True)}")
    print(f"skipped: {stats['skippedCount']} {json.dumps(reason_frequencies(output['skipped']), sort_keys=True)}")
    print(f"unresolved: {stats['unresolvedCount']} {json.dumps(reason_frequencies(output['unresolved']), sort_keys=True)}")
    print(f"warnings: {stats['warningCount']} {json.dumps(reason_frequencies(output['warnings']), sort_keys=True)}")
    print(f"phase A warnings: {stats['phaseAWarningCount']}")
    print("valid: True")


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    """Parse CLI arguments for the deterministic GitHub extractor."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT, help="Phase A corpus JSON path.")
    parser.add_argument(
        "--out",
        "--output",
        dest="output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help="Phase B nodes/edges JSON path.",
    )
    parser.add_argument("--report", action="store_true", help="Print the validation summary.")
    return parser.parse_args(argv)


def main() -> None:
    """Run Phase B, writing output only after complete validation succeeds."""
    args = parse_args()
    try:
        corpus = load_corpus(args.input)
        output = extract_corpus(corpus)
        write_output(output, args.output)
        if args.report:
            print_report(output)
            print(f"wrote: {args.output}")
    except (OSError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
