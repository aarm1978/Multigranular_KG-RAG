"""Build the Phase A normalized GitHub corpus from frozen raw downloads.

This script is an offline, deterministic preprocessor for
``data/raw/coderepos/{repo_name}/``. It parses repository metadata, manifests,
dependency files, CFF citation files, contributors, README text, and file
inventory records into the Phase A consolidated corpus:
``data/interim/coderepos/ciroh_github_corpus.json``.

Phase A is parse-and-normalize only. It does not mint KG nodes or edges, assign
ontology classes, build EvidenceSpan objects, perform network calls, execute
repository code, or consolidate identities across repositories.
"""

from __future__ import annotations

import argparse
import ast
import configparser
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

try:
    import tomllib
except ImportError:  # pragma: no cover - kept for portability if run outside py3.11.
    import tomli as tomllib  # type: ignore[no-redef]

import yaml
from packaging.requirements import InvalidRequirement, Requirement
from packaging.utils import canonicalize_name


SCHEMA_VERSION = "1.0.0"
PHASE_A_VERSION = "1.0.0"
DEFAULT_RAW_ROOT = Path("data/raw/coderepos")
DEFAULT_OUTPUT = Path("data/interim/coderepos/ciroh_github_corpus.json")
DIRECT_FILE_ROLES = {"dependency_manifest", "environment_manifest"}
LOCK_SENTINELS = {"_libgcc_mutex", "_openmp_mutex"}
BOOTSTRAP_PACKAGES = {"flit-core", "hatch-vcs", "hatchling", "pdm-backend", "pip", "poetry-core", "setuptools", "wheel"}
MANIFEST_TYPES = {
    "requirements.txt": "requirements_txt",
    "environment.yml": "environment_yml",
    "environment.yaml": "environment_yml",
    "pyproject.toml": "pyproject_toml",
    "setup.cfg": "setup_cfg",
    "setup.py": "setup_py",
    "pipfile": "pipfile",
    "pipfile.lock": "pipfile_lock",
    "poetry.lock": "poetry_lock",
}
CITATION_REFERENCE_KEYS = (
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
)
URL_RE = re.compile(r"https?://[^\s<>)\\\]\"']+")
DOI_RE = re.compile(r"\b10\.\d{4,9}/[-._;()/:A-Za-z0-9]+\b")


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments for the corpus builder."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw", type=Path, default=DEFAULT_RAW_ROOT, help="Raw code repository root.")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUTPUT, help="Output corpus JSON path.")
    parser.add_argument("--repos", nargs="*", help="Optional repo names to process.")
    parser.add_argument("--report", action="store_true", help="Print the Phase A validation summary.")
    return parser.parse_args()


def read_text_tolerant(path: Path) -> str:
    """Read a text file with UTF-8 first and a tolerant fallback, normalizing line endings."""
    raw = path.read_bytes()
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        text = raw.decode("latin-1")
    return text.replace("\r\n", "\n").replace("\r", "\n").lstrip("\ufeff")


def load_json_file(path: Path, warnings: list[dict[str, str]]) -> Any:
    """Load a JSON file, returning an empty structure and warning if parsing fails."""
    try:
        return json.loads(read_text_tolerant(path))
    except Exception as exc:  # noqa: BLE001 - parse failures become corpus warnings.
        warnings.append({"file": path.name, "issue": f"json_parse_failed: {exc}"})
        return [] if path.name in {"files_manifest.json", "contributors.json"} else {}


def source_file(repo_dir: Path, manifest_path: str) -> Path:
    """Return the local content path for a manifest-relative repository path."""
    return repo_dir / "contents" / manifest_path


def warning(file: str, issue: str) -> dict[str, str]:
    """Build a normalized parse-warning record."""
    return {"file": file, "issue": issue}


def normalize_scalar(value: Any) -> Any:
    """Convert TOML/YAML scalar values into JSON-stable primitive values."""
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    return str(value)


def toml_value(value: Any) -> str:
    """Render a parsed TOML value as a stable TOML expression for raw evidence."""
    if isinstance(value, str):
        return json.dumps(value, ensure_ascii=False)
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, list):
        return "[" + ", ".join(toml_value(item) for item in value) + "]"
    if isinstance(value, dict):
        return "{" + ", ".join(f"{key} = {toml_value(item)}" for key, item in value.items()) + "}"
    if value is None:
        return '""'
    return json.dumps(str(value), ensure_ascii=False)


def toml_assignment(name: str, value: Any) -> str:
    """Render a TOML table assignment from a parsed key/value pair."""
    return f"{name} = {toml_value(value)}"


def empty_citation(format_value: str = "none") -> dict[str, Any]:
    """Return the always-present citation block with fixed nested shapes."""
    return {
        "present": False,
        "format": format_value,
        "placeholder": False,
        "source_path": None,
        "cff_version": None,
        "type": None,
        "title": None,
        "software_authors": [],
        "doi": None,
        "version": None,
        "date_released": None,
        "url": None,
        "repository_code": None,
        "repository": None,
        "keywords": [],
        "license": None,
        "abstract": None,
        "preferred_citation": empty_citation_reference(),
        "references": [],
    }


def empty_citation_reference() -> dict[str, Any]:
    """Return the fixed paper/work citation sub-shape."""
    return {
        "type": None,
        "authors": [],
        "doi": None,
        "title": None,
        "journal": None,
        "year": None,
        "volume": None,
        "number": None,
        "start": None,
        "end": None,
        "publisher": None,
        "url": None,
    }


def derive_file_role(path: str, file_name: str, extension: str) -> str:
    """Derive the Phase A file role using the priority-ordered contract table."""
    lower_path = path.lower()
    lower_name = file_name.lower()
    lower_ext = extension.lower()
    parts = lower_path.split("/")
    if lower_name.startswith("readme"):
        return "readme"
    if lower_name.startswith(("license", "licence", "copying")):
        return "license"
    if lower_name == "citation.cff":
        return "citation_cff"
    if lower_name in {"citation", "citation.md", "citation.txt"}:
        return "citation_md"
    if lower_name.startswith("changelog"):
        return "changelog"
    if lower_name.startswith("contributing"):
        return "contributing"
    if lower_name.startswith("code_of_conduct"):
        return "code_of_conduct"
    if lower_name == "security.md":
        return "security"
    if lower_name == "dockerfile" or lower_name.startswith("dockerfile.") or lower_name == "containerfile":
        return "dockerfile"
    if (
        lower_name.startswith("requirements")
        and lower_name.endswith(".txt")
        or lower_name in {"pyproject.toml", "setup.py", "setup.cfg", "pipfile", "pipfile.lock"}
    ):
        return "dependency_manifest"
    if lower_name in {"environment.yml", "environment.yaml"}:
        return "environment_manifest"
    if lower_ext == ".ipynb":
        return "notebook"
    if parts[0] in {"docs", "doc", "documentation"} and lower_ext in {".md", ".rst", ".markdown"}:
        return "documentation"
    if parts[0] in {"examples", "tutorials"} and lower_ext in {".md", ".rst", ".markdown", ".ipynb"}:
        return "example"
    if lower_ext == ".py":
        return "source"
    if "/" not in lower_path and lower_ext in {".md", ".rst", ".markdown"}:
        return "documentation"
    return "other"


def derive_manifest_scope(path: str) -> str:
    """Classify the source manifest location as root, docs, or example scope."""
    first = path.lower().split("/", 1)[0]
    if first in {"docs", "doc", "documentation"}:
        return "docs"
    if first in {"examples", "tutorials"}:
        return "example"
    return "root"


def manifest_type_for_path(path: str) -> str:
    """Return the normalized manifest type label for a repository path."""
    name = Path(path).name.lower()
    if name.startswith("requirements") and name.endswith(".txt"):
        return "requirements_txt"
    if name.endswith("-lock.yml"):
        return "conda_lock_yml"
    return MANIFEST_TYPES.get(name, name.replace(".", "_").replace("-", "_"))


def build_source(manifest_path: str, raw_line: str | None = None) -> dict[str, Any]:
    """Build a dependency source record with manifest path, type, scope, and raw line."""
    return {
        "manifest_path": manifest_path,
        "manifest_type": manifest_type_for_path(manifest_path),
        "manifest_scope": derive_manifest_scope(manifest_path),
        "raw_line": raw_line,
    }


def build_files(files_manifest: list[dict[str, Any]]) -> dict[str, Any]:
    """Build the files block from the raw files_manifest.json records."""
    histogram = Counter(str(entry.get("selection_reason")) for entry in files_manifest)
    downloaded: list[dict[str, Any]] = []
    dockerfiles: list[dict[str, Any]] = []
    for entry in files_manifest:
        path = str(entry.get("path") or "")
        file_name = str(entry.get("file_name") or Path(path).name)
        extension = str(entry.get("extension") or "")
        file_role = derive_file_role(path, file_name, extension)
        if bool(entry.get("downloaded")):
            downloaded.append(
                {
                    "path": path,
                    "file_name": file_name,
                    "extension": extension,
                    "size_bytes": entry.get("size_bytes"),
                    "selection_reason": entry.get("selection_reason"),
                    "file_role": file_role,
                    "source_path": f"files_manifest.json:{path}",
                }
            )
        if file_role == "dockerfile":
            dockerfiles.append(
                {
                    "path": path,
                    "file_name": file_name,
                    "size_bytes": entry.get("size_bytes"),
                }
            )
    downloaded.sort(key=lambda item: item["path"])
    dockerfiles.sort(key=lambda item: item["path"])
    return {
        "total_count": len(files_manifest),
        "downloaded_count": len(downloaded),
        "selection_reason_histogram": dict(sorted(histogram.items())),
        "has_dockerfile": bool(dockerfiles),
        "downloaded": downloaded,
        "dockerfiles": dockerfiles,
    }


def build_license(metadata: dict[str, Any]) -> dict[str, Any] | None:
    """Build the license block from GitHub metadata, preserving null when absent."""
    raw_license = metadata.get("license")
    if raw_license is None:
        return None
    spdx_id = raw_license.get("spdx_id")
    is_spdx = bool(spdx_id and spdx_id != "NOASSERTION" and re.fullmatch(r"[A-Za-z0-9-.+]+", str(spdx_id)))
    return {
        "key": raw_license.get("key"),
        "name": raw_license.get("name"),
        "spdx_id": spdx_id,
        "url": raw_license.get("url"),
        "is_spdx": is_spdx,
        "source_path": "repo_metadata.json:license",
    }


def build_identifiers(metadata: dict[str, Any], archive: dict[str, Any], citation: dict[str, Any]) -> list[dict[str, Any]]:
    """Build sorted repository identifiers from metadata, archive, and CFF DOI."""
    identifiers: list[dict[str, Any]] = []
    if metadata.get("html_url"):
        identifiers.append(
            {
                "id_type": "repo_url",
                "value": metadata.get("html_url"),
                "source_path": "repo_metadata.json:html_url",
            }
        )
    if archive.get("frozen_commit_sha"):
        identifiers.append(
            {
                "id_type": "commit_sha",
                "value": archive.get("frozen_commit_sha"),
                "source_path": "archive_info.json:frozen_commit_sha",
            }
        )
    if citation.get("doi"):
        identifiers.append(
            {
                "id_type": "doi",
                "value": citation.get("doi"),
                "source_path": f"{citation.get('source_path')}:doi",
            }
        )
    return sorted(identifiers, key=lambda item: (str(item["id_type"]), str(item["value"])))


def build_contributors(contributors: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Build sorted contributor records from contributors.json."""
    records = []
    for index, contributor in enumerate(contributors):
        contributor_type = contributor.get("type")
        records.append(
            {
                "github_id": contributor.get("id"),
                "login": contributor.get("login"),
                "html_url": contributor.get("html_url"),
                "type": contributor_type,
                "contributions": contributor.get("contributions"),
                "is_bot": contributor_type == "Bot",
                "source_path": f"contributors.json[{index}]",
            }
        )
    return sorted(records, key=lambda item: (item["github_id"] is None, item["github_id"] or 0, item["login"] or ""))


def is_symlink_as_text(text: str) -> bool:
    """Return true when a YAML file body is just a bare filesystem path."""
    stripped = text.strip()
    return bool(stripped and "\n" not in stripped and re.match(r"^(\.\.?/|/|[A-Za-z]:\\)", stripped))


def strip_inline_comment(line: str) -> str:
    """Strip a simple inline comment while preserving URL fragments used by VCS requirements."""
    if "://" in line and "#egg=" in line:
        return line.strip()
    return re.sub(r"\s+#.*$", "", line).strip()


def normalize_vcs_url(raw_url: str) -> str:
    """Normalize a VCS URL to a stable HTTPS repository URL when possible."""
    url = raw_url.strip()
    if url.startswith("git+"):
        url = url[4:]
    url = url.split("#", 1)[0]
    if "@" in url:
        scheme_split = url.split("://", 1)
        if len(scheme_split) == 2:
            scheme, rest = scheme_split
            if "@" in rest:
                before, after = rest.rsplit("@", 1)
                if "/" not in after and not after.endswith(".git"):
                    url = f"{scheme}://{before}"
    url = url.rstrip("/")
    if url.endswith(".git"):
        url = url[:-4]
    if url.startswith("git@github.com:"):
        url = "https://github.com/" + url.removeprefix("git@github.com:")
    return url


def parse_vcs_requirement(raw: str) -> dict[str, Any] | None:
    """Parse a VCS dependency string into normalized repository dependency fields."""
    text = raw.strip()
    name_prefix = None
    vcs_part = text
    if " @ git+" in text:
        name_prefix, vcs_part = text.split(" @ ", 1)
    if not vcs_part.startswith("git+"):
        return None
    fragment = ""
    if "#" in vcs_part:
        vcs_part, fragment = vcs_part.split("#", 1)
    parsed_fragment = parse_qs(fragment, keep_blank_values=True)
    egg = parsed_fragment.get("egg", [None])[0]
    subdirectory = parsed_fragment.get("subdirectory", [None])[0]
    ref = None
    url_without_git = vcs_part[4:]
    parsed = urlparse(url_without_git)
    if "@" in parsed.path:
        path_part, ref = parsed.path.rsplit("@", 1)
        url_without_git = parsed._replace(path=path_part).geturl()
    name = name_prefix or egg or Path(urlparse(url_without_git).path).name.removesuffix(".git")
    return {
        "name": canonicalize_name(name) if name else None,
        "vcs_url": normalize_vcs_url("git+" + url_without_git),
        "ref": ref,
        "subdirectory": subdirectory,
        "egg": egg,
    }


def parse_conda_requirement(raw: str) -> tuple[str | None, str | None]:
    """Parse a conda requirement name and version spec from a string entry."""
    text = raw.strip()
    if not text or text.startswith("#"):
        return None, None
    parts = text.split("=")
    name = parts[0].strip()
    if not name:
        return None, None
    if len(parts) == 1:
        return canonicalize_name(name), None
    return canonicalize_name(name), "=".join(parts[1:]).strip() or None


def strip_conda_build_from_python_version(version: str | None) -> str | None:
    """Strip a conda build string from python_version while preserving the version."""
    if version is None:
        return None
    return version.split("=", 1)[0]


def normalize_requirement(raw: str, ecosystem: str, dep_group: str) -> dict[str, Any] | None:
    """Normalize one direct requirement into the documented dependency struct."""
    cleaned = strip_inline_comment(raw)
    if not cleaned:
        return None
    vcs = parse_vcs_requirement(cleaned)
    if vcs:
        return {
            "name": vcs["name"],
            "raw": raw,
            "version_spec": None,
            "extras": [],
            "marker": None,
            "ecosystem": ecosystem,
            "dep_group": dep_group,
            "is_vcs": True,
            "vcs_url": vcs["vcs_url"],
            "ref": vcs["ref"],
            "subdirectory": vcs["subdirectory"],
            "egg": vcs["egg"],
        }
    if ecosystem == "conda":
        name, version_spec = parse_conda_requirement(cleaned)
        if not name:
            return None
        return {
            "name": name,
            "raw": raw,
            "version_spec": version_spec,
            "extras": [],
            "marker": None,
            "ecosystem": ecosystem,
            "dep_group": dep_group,
            "is_vcs": False,
            "vcs_url": None,
            "ref": None,
            "subdirectory": None,
            "egg": None,
        }
    try:
        requirement = Requirement(cleaned)
    except InvalidRequirement:
        if "git+" in cleaned:
            vcs = parse_vcs_requirement(cleaned.split(" @ ", 1)[-1])
            if vcs:
                return {
                    "name": vcs["name"],
                    "raw": raw,
                    "version_spec": None,
                    "extras": [],
                    "marker": None,
                    "ecosystem": ecosystem,
                    "dep_group": dep_group,
                    "is_vcs": True,
                    "vcs_url": vcs["vcs_url"],
                    "ref": vcs["ref"],
                    "subdirectory": vcs["subdirectory"],
                    "egg": vcs["egg"],
                }
        return None
    return {
        "name": canonicalize_name(requirement.name),
        "raw": raw,
        "version_spec": str(requirement.specifier) or None,
        "extras": sorted(requirement.extras),
        "marker": str(requirement.marker) if requirement.marker else None,
        "ecosystem": ecosystem,
        "dep_group": dep_group,
        "is_vcs": False,
        "vcs_url": None,
        "ref": None,
        "subdirectory": None,
        "egg": None,
    }


def normalize_poetry_package_requirement(name: str, value: str, dep_group: str, raw: str) -> dict[str, Any] | None:
    """Normalize a non-VCS Poetry package entry, preserving Poetry-native constraints."""
    if name.lower() == "python":
        return None
    try:
        requirement_name = Requirement(name)
        normalized_name = canonicalize_name(requirement_name.name)
        extras = sorted(requirement_name.extras)
    except InvalidRequirement:
        normalized_name = canonicalize_name(name)
        extras = []
    return {
        "name": normalized_name,
        "raw": raw,
        "version_spec": None if value == "*" else value,
        "extras": extras,
        "marker": None,
        "ecosystem": "pypi",
        "dep_group": dep_group,
        "is_vcs": False,
        "vcs_url": None,
        "ref": None,
        "subdirectory": None,
        "egg": None,
    }


def add_dependency(
    accum: dict[tuple[str, bool, str | None], dict[str, Any]],
    requirement: dict[str, Any],
    source: dict[str, Any],
) -> None:
    """Add or merge a dependency within one repository using the contract dedup key."""
    if requirement["name"] in {"python", "python-version"}:
        return
    if requirement["name"] in BOOTSTRAP_PACKAGES:
        return
    key = (requirement["name"], bool(requirement["is_vcs"]), requirement.get("vcs_url"))
    if key not in accum:
        record = {k: requirement[k] for k in ("name", "raw", "version_spec", "extras", "marker", "ecosystem", "dep_group", "is_vcs")}
        if requirement["is_vcs"]:
            record.update(
                {
                    "vcs_url": requirement["vcs_url"],
                    "ref": requirement["ref"],
                    "subdirectory": requirement["subdirectory"],
                    "egg": requirement["egg"],
                }
            )
        record["sources"] = []
        accum[key] = record
    else:
        precedence = {"runtime": 4, "optional": 3, "dev": 2, "build": 1}
        if precedence.get(requirement["dep_group"], 0) > precedence.get(accum[key]["dep_group"], 0):
            accum[key]["dep_group"] = requirement["dep_group"]
    accum[key]["sources"].append(source)


def sorted_dependencies(accum: dict[tuple[str, bool, str | None], dict[str, Any]], vcs: bool) -> list[dict[str, Any]]:
    """Return dependency records sorted with sorted source lists."""
    records = [record for (_name, is_vcs, _url), record in accum.items() if is_vcs is vcs]
    for record in records:
        record["sources"] = sorted(record["sources"], key=lambda item: (item["manifest_path"], item["raw_line"] or ""))
    return sorted(records, key=lambda item: (item["name"] or "", item.get("vcs_url") or "", item["dep_group"]))


def classify_requirements_lines(lines: list[str]) -> str:
    """Classify requirements.txt lines as direct or lock."""
    requirements = [
        strip_inline_comment(line)
        for line in lines
        if strip_inline_comment(line) and not strip_inline_comment(line).startswith(("-r", "-c", "-e", "#"))
    ]
    if not requirements:
        return "direct"
    marker_count = sum(";" in line and "python_version" in line for line in requirements)
    pinned_count = sum("==" in line for line in requirements)
    transitive_hits = sum(
        any(name in line.lower() for name in ("certifi", "charset-normalizer", "urllib3", "idna", "six"))
        for line in requirements
    )
    if marker_count >= max(1, int(len(requirements) * 0.8)):
        return "lock"
    if len(requirements) >= 60 and pinned_count >= 60 and transitive_hits >= 2:
        return "lock"
    return "direct"


def classify_environment_yaml(parsed: Any) -> str:
    """Classify an environment YAML object as direct or lock."""
    if not isinstance(parsed, dict):
        return "direct"
    dependencies = parsed.get("dependencies") or []
    if parsed.get("prefix"):
        return "lock"
    for dep in dependencies:
        if isinstance(dep, str):
            name = dep.split("=", 1)[0].strip()
            if name in LOCK_SENTINELS or dep.count("=") >= 2:
                return "lock"
    return "direct"


def pinned_evidence_from_lines(lines: list[str]) -> list[str]:
    """Return non-empty, non-comment lock evidence lines preserving original order."""
    evidence = []
    for line in lines:
        stripped = line.strip()
        if stripped and not stripped.startswith("#"):
            evidence.append(stripped)
    return evidence


def add_python_environment(
    execution_environment: list[dict[str, Any]],
    source_path: str,
    python_version: str | None,
) -> None:
    """Append a python constraint execution-environment record when a value exists."""
    if python_version:
        execution_environment.append(
            {
                "kind": "python_constraint",
                "name": None,
                "channels": [],
                "python_version": python_version,
                "prefix": None,
                "is_lock": False,
                "pinned_count": None,
                "pinned_set_evidence": None,
                "source_path": source_path,
            }
        )


def parse_requirements_txt(
    manifest_path: str,
    text: str,
    dependencies: dict[tuple[str, bool, str | None], dict[str, Any]],
    execution_environment: list[dict[str, Any]],
    warnings: list[dict[str, str]],
) -> str:
    """Parse a requirements.txt manifest and return its direct/lock classification."""
    lines = text.split("\n")
    classification = classify_requirements_lines(lines)
    if classification == "lock":
        evidence = pinned_evidence_from_lines(lines)
        execution_environment.append(
            {
                "kind": "requirements_lock",
                "name": None,
                "channels": [],
                "python_version": None,
                "prefix": None,
                "is_lock": True,
                "pinned_count": len(evidence),
                "pinned_set_evidence": evidence,
                "source_path": manifest_path,
            }
        )
        return classification
    for line in lines:
        raw_line = line.strip()
        cleaned = strip_inline_comment(raw_line)
        if not cleaned or cleaned.startswith("#"):
            continue
        if cleaned.startswith(("-r", "-c")):
            warnings.append(warning(manifest_path, f"include_directive_skipped: {cleaned}"))
            continue
        if cleaned.startswith("-e"):
            warnings.append(warning(manifest_path, f"editable_self_reference_skipped: {cleaned}"))
            continue
        requirement = normalize_requirement(cleaned, "pypi", "runtime")
        if requirement is None:
            warnings.append(warning(manifest_path, f"requirement_unparseable: {cleaned}"))
            continue
        add_dependency(dependencies, requirement, build_source(manifest_path, cleaned))
    return classification


def parse_environment_yml(
    manifest_path: str,
    text: str,
    dependencies: dict[tuple[str, bool, str | None], dict[str, Any]],
    execution_environment: list[dict[str, Any]],
    warnings: list[dict[str, str]],
) -> str | None:
    """Parse a conda environment manifest and return direct/lock/skipped classification."""
    if is_symlink_as_text(text):
        warnings.append(warning(manifest_path, "symlink_as_text_environment_skipped"))
        return None
    try:
        parsed = yaml.safe_load(text) or {}
    except Exception as exc:  # noqa: BLE001 - contract says warn rather than crash.
        warnings.append(warning(manifest_path, f"yaml_parse_failed: {exc}"))
        return None
    if not isinstance(parsed, dict):
        warnings.append(warning(manifest_path, "environment_yaml_not_mapping_skipped"))
        return None
    classification = classify_environment_yaml(parsed)
    deps = parsed.get("dependencies") or []
    channels = parsed.get("channels") if isinstance(parsed.get("channels"), list) else []
    python_version = None
    conda_evidence: list[str] = []
    for dep in deps:
        if isinstance(dep, str):
            name, version = parse_conda_requirement(dep)
            if name == "python":
                python_version = strip_conda_build_from_python_version(version)
            conda_evidence.append(dep)
        elif isinstance(dep, dict) and isinstance(dep.get("pip"), list):
            conda_evidence.extend(str(item) for item in dep.get("pip") or [])
    execution_environment.append(
        {
            "kind": "conda_env",
            "name": parsed.get("name"),
            "channels": [str(channel) for channel in channels],
            "python_version": python_version,
            "prefix": parsed.get("prefix"),
            "is_lock": classification == "lock",
            "pinned_count": len(conda_evidence) if classification == "lock" else None,
            "pinned_set_evidence": conda_evidence if classification == "lock" else None,
            "source_path": manifest_path,
        }
    )
    if classification == "lock":
        return classification
    for dep in deps:
        if isinstance(dep, str):
            requirement = normalize_requirement(dep, "conda", "runtime")
            if requirement is None or requirement["name"] == "python":
                continue
            add_dependency(dependencies, requirement, build_source(manifest_path, dep))
        elif isinstance(dep, dict) and isinstance(dep.get("pip"), list):
            for pip_dep in dep["pip"]:
                requirement = normalize_requirement(str(pip_dep), "pypi", "runtime")
                if requirement is None:
                    warnings.append(warning(manifest_path, f"pip_requirement_unparseable: {pip_dep}"))
                    continue
                add_dependency(dependencies, requirement, build_source(manifest_path, str(pip_dep)))
    return classification


def normalize_poetry_requirement(name: str, value: Any, dep_group: str) -> dict[str, Any] | None:
    """Normalize a Poetry dependency table entry."""
    if name.lower() == "python":
        return None
    raw = toml_assignment(name, value)
    if isinstance(value, str):
        return normalize_poetry_package_requirement(name, value, dep_group, raw)
    if isinstance(value, dict) and "git" in value:
        git_url = str(value["git"])
        ref = value.get("rev") or value.get("tag") or value.get("branch")
        requirement = normalize_requirement(f"{name} @ git+{git_url}" + (f"@{ref}" if ref else ""), "pypi", dep_group)
        if requirement is not None:
            requirement["raw"] = raw
        return requirement
    if isinstance(value, dict) and "version" in value:
        return normalize_poetry_package_requirement(name, str(value["version"]), dep_group, raw)
    return normalize_requirement(name, "pypi", dep_group)


def parse_pyproject_toml(
    manifest_path: str,
    text: str,
    dependencies: dict[tuple[str, bool, str | None], dict[str, Any]],
    execution_environment: list[dict[str, Any]],
    software_metadata: list[dict[str, Any]],
    warnings: list[dict[str, str]],
) -> str:
    """Parse pyproject.toml for dependencies, python constraints, and software metadata."""
    try:
        parsed = tomllib.loads(text)
    except Exception as exc:  # noqa: BLE001
        warnings.append(warning(manifest_path, f"toml_parse_failed: {exc}"))
        return "direct"
    project = parsed.get("project") if isinstance(parsed.get("project"), dict) else {}
    poetry = parsed.get("tool", {}).get("poetry", {}) if isinstance(parsed.get("tool"), dict) else {}
    build_system = parsed.get("build-system") if isinstance(parsed.get("build-system"), dict) else {}
    if project:
        for dep in project.get("dependencies") or []:
            requirement = normalize_requirement(str(dep), "pypi", "runtime")
            if requirement:
                add_dependency(dependencies, requirement, build_source(manifest_path, str(dep)))
        for group, group_deps in (project.get("optional-dependencies") or {}).items():
            for dep in group_deps or []:
                requirement = normalize_requirement(str(dep), "pypi", "optional")
                if requirement:
                    add_dependency(dependencies, requirement, build_source(manifest_path, str(dep)))
        add_python_environment(execution_environment, manifest_path, project.get("requires-python"))
        authors = [
            {"name": author.get("name"), "email": author.get("email")}
            for author in project.get("authors") or []
            if isinstance(author, dict)
        ]
        software_metadata.append(
            {
                "name": project.get("name"),
                "version": project.get("version"),
                "authors": authors,
                "urls": project.get("urls") or {},
                "license": normalize_scalar(project.get("license")),
                "manifest_type": "pyproject_toml",
                "source_path": manifest_path,
            }
        )
    if poetry:
        for name, value in (poetry.get("dependencies") or {}).items():
            requirement = normalize_poetry_requirement(str(name), value, "runtime")
            if requirement:
                add_dependency(dependencies, requirement, build_source(manifest_path, requirement["raw"]))
            elif str(name).lower() == "python":
                add_python_environment(execution_environment, manifest_path, str(value))
        for name, value in (poetry.get("dev-dependencies") or {}).items():
            requirement = normalize_poetry_requirement(str(name), value, "dev")
            if requirement:
                add_dependency(dependencies, requirement, build_source(manifest_path, requirement["raw"]))
        for group_data in (poetry.get("group") or {}).values():
            if isinstance(group_data, dict):
                for name, value in (group_data.get("dependencies") or {}).items():
                    requirement = normalize_poetry_requirement(str(name), value, "dev")
                    if requirement:
                        add_dependency(dependencies, requirement, build_source(manifest_path, requirement["raw"]))
        authors = [{"name": author, "email": None} for author in poetry.get("authors") or []]
        software_metadata.append(
            {
                "name": poetry.get("name"),
                "version": poetry.get("version"),
                "authors": authors,
                "urls": {"repository": poetry.get("repository"), "homepage": poetry.get("homepage")},
                "license": poetry.get("license"),
                "manifest_type": "pyproject_toml",
                "source_path": manifest_path,
            }
        )
    for dep in build_system.get("requires") or []:
        requirement = normalize_requirement(str(dep), "pypi", "build")
        if requirement:
            add_dependency(dependencies, requirement, build_source(manifest_path, str(dep)))
    return "direct"


def parse_setup_cfg(
    manifest_path: str,
    text: str,
    dependencies: dict[tuple[str, bool, str | None], dict[str, Any]],
    execution_environment: list[dict[str, Any]],
    software_metadata: list[dict[str, Any]],
    warnings: list[dict[str, str]],
) -> str:
    """Parse setup.cfg for install requirements, extras, python constraints, and metadata."""
    parser = configparser.ConfigParser()
    try:
        parser.read_string(text)
    except configparser.Error as exc:
        warnings.append(warning(manifest_path, f"ini_parse_failed: {exc}"))
        return "direct"
    if parser.has_option("options", "install_requires"):
        for dep in parser.get("options", "install_requires").splitlines():
            cleaned = dep.strip()
            if cleaned:
                requirement = normalize_requirement(cleaned, "pypi", "runtime")
                if requirement:
                    add_dependency(dependencies, requirement, build_source(manifest_path, cleaned))
    if parser.has_section("options.extras_require"):
        for _group, value in parser.items("options.extras_require"):
            for dep in value.splitlines():
                cleaned = dep.strip()
                if cleaned:
                    requirement = normalize_requirement(cleaned, "pypi", "optional")
                    if requirement:
                        add_dependency(dependencies, requirement, build_source(manifest_path, cleaned))
    if parser.has_option("options", "python_requires"):
        add_python_environment(execution_environment, manifest_path, parser.get("options", "python_requires"))
    if parser.has_section("metadata"):
        author = parser.get("metadata", "author", fallback=None)
        email = parser.get("metadata", "author_email", fallback=None)
        urls: dict[str, str | None] = {"url": parser.get("metadata", "url", fallback=None)}
        if parser.has_option("metadata", "project_urls"):
            for line in parser.get("metadata", "project_urls").splitlines():
                if "=" in line:
                    key, value = line.split("=", 1)
                    urls[key.strip()] = value.strip()
        software_metadata.append(
            {
                "name": parser.get("metadata", "name", fallback=None),
                "version": parser.get("metadata", "version", fallback=None),
                "authors": [{"name": author, "email": email}] if author or email else [],
                "urls": urls,
                "license": parser.get("metadata", "license", fallback=None),
                "manifest_type": "setup_cfg",
                "source_path": manifest_path,
            }
        )
    return "direct"


def literal_or_none(node: ast.AST) -> Any:
    """Return ast.literal_eval for a node, or None if it is dynamic."""
    try:
        return ast.literal_eval(node)
    except Exception:  # noqa: BLE001
        return None


def parse_setup_py(
    manifest_path: str,
    text: str,
    dependencies: dict[tuple[str, bool, str | None], dict[str, Any]],
    warnings: list[dict[str, str]],
) -> str:
    """Statically parse setup.py literals without executing repository code."""
    try:
        tree = ast.parse(text)
    except SyntaxError as exc:
        warnings.append(warning(manifest_path, f"setup_py_syntax_error: {exc}"))
        return "direct"
    setup_call = None
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Name) and func.id == "setup":
                setup_call = node
                break
            if isinstance(func, ast.Attribute) and func.attr == "setup":
                setup_call = node
                break
    if setup_call is None:
        warnings.append(warning(manifest_path, "setup_py_no_setup_call"))
        return "direct"
    saw_deps = False
    for keyword in setup_call.keywords:
        if keyword.arg == "install_requires":
            saw_deps = True
            value = literal_or_none(keyword.value)
            if not isinstance(value, list):
                warnings.append(warning(manifest_path, "setup_py_install_requires_deferred_unparseable"))
                continue
            for dep in value:
                requirement = normalize_requirement(str(dep), "pypi", "runtime")
                if requirement:
                    add_dependency(dependencies, requirement, build_source(manifest_path, str(dep)))
        if keyword.arg == "extras_require":
            saw_deps = True
            value = literal_or_none(keyword.value)
            if not isinstance(value, dict):
                warnings.append(warning(manifest_path, "setup_py_extras_require_deferred_unparseable"))
                continue
            for deps in value.values():
                for dep in deps if isinstance(deps, list) else []:
                    requirement = normalize_requirement(str(dep), "pypi", "optional")
                    if requirement:
                        add_dependency(dependencies, requirement, build_source(manifest_path, str(dep)))
    if not saw_deps:
        warnings.append(warning(manifest_path, "setup_py_deps_absent_deferred_unparseable"))
    return "direct"


def parse_pipfile(
    manifest_path: str,
    text: str,
    dependencies: dict[tuple[str, bool, str | None], dict[str, Any]],
    execution_environment: list[dict[str, Any]],
    warnings: list[dict[str, str]],
) -> str:
    """Parse Pipfile dependency and python-version fields."""
    try:
        parsed = tomllib.loads(text)
    except Exception as exc:  # noqa: BLE001
        warnings.append(warning(manifest_path, f"toml_parse_failed: {exc}"))
        return "direct"
    for section, dep_group in (("packages", "runtime"), ("dev-packages", "dev")):
        for name, value in (parsed.get(section) or {}).items():
            requirement = normalize_poetry_requirement(str(name), value, dep_group)
            if requirement:
                add_dependency(dependencies, requirement, build_source(manifest_path, requirement["raw"]))
    requires = parsed.get("requires") if isinstance(parsed.get("requires"), dict) else {}
    add_python_environment(execution_environment, manifest_path, requires.get("python_version"))
    return "direct"


def parse_pipfile_lock(manifest_path: str, text: str, execution_environment: list[dict[str, Any]]) -> str:
    """Parse Pipfile.lock as lock evidence only, preserving package order from JSON."""
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        parsed = {}
    default = list((parsed.get("default") or {}).keys()) if isinstance(parsed, dict) else []
    develop = list((parsed.get("develop") or {}).keys()) if isinstance(parsed, dict) else []
    evidence = default + develop
    execution_environment.append(
        {
            "kind": "pipfile_lock",
            "name": None,
            "channels": [],
            "python_version": None,
            "prefix": None,
            "is_lock": True,
            "pinned_count": len(evidence),
            "pinned_set_evidence": evidence,
            "source_path": manifest_path,
        }
    )
    return "lock"


def parse_manifest(
    repo_dir: Path,
    file_record: dict[str, Any],
    dependencies: dict[tuple[str, bool, str | None], dict[str, Any]],
    execution_environment: list[dict[str, Any]],
    software_metadata: list[dict[str, Any]],
    warnings: list[dict[str, str]],
    manifest_classifications: dict[str, str],
) -> None:
    """Dispatch one downloaded dependency/environment manifest to its parser."""
    manifest_path = file_record["path"]
    path = source_file(repo_dir, manifest_path)
    text = read_text_tolerant(path)
    name = Path(manifest_path).name.lower()
    classification: str | None
    if name.startswith("requirements") and name.endswith(".txt"):
        classification = parse_requirements_txt(manifest_path, text, dependencies, execution_environment, warnings)
    elif name in {"environment.yml", "environment.yaml"} or name.endswith("-lock.yml"):
        classification = parse_environment_yml(manifest_path, text, dependencies, execution_environment, warnings)
    elif name == "pyproject.toml":
        classification = parse_pyproject_toml(manifest_path, text, dependencies, execution_environment, software_metadata, warnings)
    elif name == "setup.cfg":
        classification = parse_setup_cfg(manifest_path, text, dependencies, execution_environment, software_metadata, warnings)
    elif name == "setup.py":
        classification = parse_setup_py(manifest_path, text, dependencies, warnings)
    elif name == "pipfile":
        classification = parse_pipfile(manifest_path, text, dependencies, execution_environment, warnings)
    elif name == "pipfile.lock":
        classification = parse_pipfile_lock(manifest_path, text, execution_environment)
    elif name == "poetry.lock":
        evidence = pinned_evidence_from_lines(text.split("\n"))
        execution_environment.append(
            {
                "kind": "poetry_lock",
                "name": None,
                "channels": [],
                "python_version": None,
                "prefix": None,
                "is_lock": True,
                "pinned_count": len(evidence),
                "pinned_set_evidence": evidence,
                "source_path": manifest_path,
            }
        )
        classification = "lock"
    else:
        classification = "direct"
        warnings.append(warning(manifest_path, "manifest_type_unhandled"))
    if classification:
        manifest_classifications[manifest_path] = classification


def cff_author(author: Any, include_email: bool = False, include_affiliation: bool = False) -> dict[str, Any]:
    """Normalize a CFF author object to the fixed author shape."""
    if not isinstance(author, dict):
        base = {"family_names": None, "given_names": normalize_scalar(author), "orcid": None}
    else:
        base = {
            "family_names": normalize_scalar(author.get("family-names")),
            "given_names": normalize_scalar(author.get("given-names")),
            "orcid": normalize_scalar(author.get("orcid")),
        }
    if include_affiliation:
        base["affiliation"] = normalize_scalar(author.get("affiliation")) if isinstance(author, dict) else None
    if include_email:
        base["email"] = normalize_scalar(author.get("email")) if isinstance(author, dict) else None
    return base


def parse_citation_reference(data: Any) -> dict[str, Any]:
    """Parse preferred-citation or references[] into the fixed citation subset."""
    result = empty_citation_reference()
    if not isinstance(data, dict):
        return result
    result.update(
        {
            "type": normalize_scalar(data.get("type")),
            "authors": [cff_author(author) for author in data.get("authors") or []],
            "doi": normalize_scalar(data.get("doi")),
            "title": normalize_scalar(data.get("title")),
            "journal": normalize_scalar(data.get("journal")),
            "year": normalize_scalar(data.get("year")),
            "volume": normalize_scalar(data.get("volume")),
            "number": normalize_scalar(data.get("number")),
            "start": normalize_scalar(data.get("start")),
            "end": normalize_scalar(data.get("end")),
            "publisher": normalize_scalar(data.get("publisher")),
            "url": normalize_scalar(data.get("url")),
        }
    )
    return result


def is_placeholder_cff(parsed: dict[str, Any], text: str) -> bool:
    """Detect cffinit placeholder content that should not seed authors."""
    title = str(parsed.get("title") or "")
    authors = parsed.get("authors") or []
    author_names = " ".join(
        " ".join(str(v) for v in author.values() if v is not None) if isinstance(author, dict) else str(author)
        for author in authors
    )
    return bool("FIXME" in text or title.strip().upper() == "FIXME" or (bool(authors) and set(author_names.upper().split()) == {"FIXME"}))


def parse_citation(downloaded_files: list[dict[str, Any]], repo_dir: Path, warnings: list[dict[str, str]]) -> tuple[dict[str, Any], dict[str, Any] | None]:
    """Parse CITATION.cff or record Markdown citation as deferred prose."""
    cff_files = [item for item in downloaded_files if item["file_role"] == "citation_cff"]
    md_files = [item for item in downloaded_files if item["file_role"] == "citation_md"]
    if cff_files:
        file_record = sorted(cff_files, key=lambda item: item["path"])[0]
        text = read_text_tolerant(source_file(repo_dir, file_record["path"]))
        citation = empty_citation("cff")
        citation["source_path"] = file_record["path"]
        try:
            parsed = yaml.safe_load(text) or {}
        except Exception as exc:  # noqa: BLE001
            warnings.append(warning(file_record["path"], f"cff_parse_failed: {exc}"))
            return citation, None
        if not isinstance(parsed, dict):
            warnings.append(warning(file_record["path"], "cff_not_mapping"))
            return citation, None
        placeholder = bool(is_placeholder_cff(parsed, text))
        citation.update(
            {
                "present": True,
                "placeholder": placeholder,
                "cff_version": normalize_scalar(parsed.get("cff-version")),
                "type": normalize_scalar(parsed.get("type")),
                "title": normalize_scalar(parsed.get("title")),
                "software_authors": []
                if placeholder
                else [cff_author(author, include_email=True, include_affiliation=True) for author in parsed.get("authors") or []],
                "doi": normalize_scalar(parsed.get("doi")),
                "version": normalize_scalar(parsed.get("version")),
                "date_released": normalize_scalar(parsed.get("date-released")),
                "url": normalize_scalar(parsed.get("url")),
                "repository_code": normalize_scalar(parsed.get("repository-code")),
                "repository": normalize_scalar(parsed.get("repository")),
                "keywords": [normalize_scalar(keyword) for keyword in parsed.get("keywords") or []],
                "license": normalize_scalar(parsed.get("license")),
                "abstract": normalize_scalar(parsed.get("abstract")),
                "preferred_citation": parse_citation_reference(parsed.get("preferred-citation")),
                "references": [parse_citation_reference(item) for item in parsed.get("references") or []],
            }
        )
        if placeholder:
            warnings.append(warning(file_record["path"], "cff_placeholder_detected"))
        return citation, None
    if md_files:
        file_record = sorted(md_files, key=lambda item: item["path"])[0]
        citation = empty_citation("md")
        return citation, {"present": True, "source_path": file_record["path"], "deferred_to_llm": True}
    return empty_citation("none"), None


def classify_url(url: str) -> str:
    """Classify a deterministic README URL for the Phase A URL buckets."""
    lower = url.lower().rstrip(".,)")
    if "hydroshare.org" in lower:
        return "hydroshare"
    if "github.com" in lower:
        return "github"
    if DOI_RE.search(lower) or "doi.org/" in lower:
        return "dois"
    return "other"


def parse_readme(downloaded_files: list[dict[str, Any]], repo_dir: Path) -> dict[str, Any]:
    """Carry README text and mechanically extracted URL buckets for Phase B."""
    readmes = sorted([item for item in downloaded_files if item["file_role"] == "readme"], key=lambda item: item["path"])
    if not readmes:
        return {
            "present": False,
            "source_path": None,
            "text": None,
            "deterministic_urls": {"hydroshare": [], "github": [], "dois": [], "other": []},
        }
    file_record = readmes[0]
    text = read_text_tolerant(source_file(repo_dir, file_record["path"]))
    buckets: dict[str, set[str]] = {"hydroshare": set(), "github": set(), "dois": set(), "other": set()}
    for url in URL_RE.findall(text):
        cleaned = url.rstrip(".,)")
        buckets[classify_url(cleaned)].add(cleaned)
    for doi in DOI_RE.findall(text):
        buckets["dois"].add(doi.rstrip(".,)"))
    return {
        "present": True,
        "source_path": file_record["path"],
        "text": text,
        "deterministic_urls": {key: sorted(values) for key, values in buckets.items()},
    }


def sort_software_metadata(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Sort software metadata records deterministically."""
    for record in records:
        record["authors"] = sorted(record["authors"], key=lambda item: (item.get("name") or "", item.get("email") or ""))
        record["urls"] = dict(sorted((record.get("urls") or {}).items()))
    return sorted(records, key=lambda item: (item.get("source_path") or "", item.get("name") or ""))


def build_source_artifact(metadata: dict[str, Any], archive: dict[str, Any], warnings: list[dict[str, str]]) -> str | None:
    """Build the SHA-pinned canonical GitHub source artifact URL for provenance."""
    html_url = metadata.get("html_url")
    frozen_commit_sha = archive.get("frozen_commit_sha")
    if not html_url or not frozen_commit_sha:
        warnings.append(warning("provenance", "source_artifact_missing_html_url_or_frozen_commit_sha"))
        return None
    return f"{str(html_url).rstrip('/')}/tree/{frozen_commit_sha}"


def build_repo_record(repo_dir: Path) -> dict[str, Any]:
    """Build one normalized repository record from a raw repository directory."""
    warnings: list[dict[str, str]] = []
    metadata = load_json_file(repo_dir / "repo_metadata.json", warnings)
    archive = load_json_file(repo_dir / "archive_info.json", warnings)
    files_manifest = load_json_file(repo_dir / "files_manifest.json", warnings)
    contributors = load_json_file(repo_dir / "contributors.json", warnings)
    files = build_files(files_manifest if isinstance(files_manifest, list) else [])
    downloaded_files = files["downloaded"]
    citation, citation_md = parse_citation(downloaded_files, repo_dir, warnings)
    dependencies_accum: dict[tuple[str, bool, str | None], dict[str, Any]] = {}
    execution_environment: list[dict[str, Any]] = []
    software_metadata: list[dict[str, Any]] = []
    manifest_classifications: dict[str, str] = {}
    for file_record in downloaded_files:
        if file_record["file_role"] in DIRECT_FILE_ROLES:
            parse_manifest(
                repo_dir,
                file_record,
                dependencies_accum,
                execution_environment,
                software_metadata,
                warnings,
                manifest_classifications,
            )
    record = {
        "repo_id": metadata.get("id"),
        "name": metadata.get("name") or repo_dir.name,
        "full_name": metadata.get("full_name"),
        "html_url": metadata.get("html_url"),
        "description": metadata.get("description"),
        "homepage": metadata.get("homepage"),
        "default_branch": metadata.get("default_branch") or archive.get("default_branch"),
        "language": metadata.get("language"),
        "topics": metadata.get("topics") or [],
        "fork": bool(metadata.get("fork")),
        "fork_parent": None,
        "archived": bool(metadata.get("archived")),
        "disabled": bool(metadata.get("disabled")),
        "visibility": metadata.get("visibility"),
        "timestamps": {
            "created_at": metadata.get("created_at"),
            "updated_at": metadata.get("updated_at"),
            "pushed_at": metadata.get("pushed_at"),
        },
        "github_stats": {
            "size_kb": metadata.get("size_kb"),
            "stargazers_count": metadata.get("stargazers_count"),
            "watchers_count": metadata.get("watchers_count"),
            "forks_count": metadata.get("forks_count"),
            "open_issues_count": metadata.get("open_issues_count"),
        },
        "archive": {
            "frozen_commit_sha": archive.get("frozen_commit_sha"),
            "downloaded_at_epoch": archive.get("downloaded_at_epoch"),
            "archive_format": archive.get("archive_format"),
        },
        "license": build_license(metadata),
        "identifiers": build_identifiers(metadata, archive, citation),
        "contributors": build_contributors(contributors if isinstance(contributors, list) else []),
        "files": files,
        "dependencies": sorted_dependencies(dependencies_accum, vcs=False),
        "repo_dependencies": sorted_dependencies(dependencies_accum, vcs=True),
        "execution_environment": sorted(execution_environment, key=lambda item: (item["source_path"], item["kind"], item.get("python_version") or "")),
        "citation": citation,
        "citation_md": citation_md,
        "software_metadata": sort_software_metadata(software_metadata),
        "readme": parse_readme(downloaded_files, repo_dir),
        "provenance": {
            "source_artifact": build_source_artifact(metadata, archive, warnings),
            "phase_a_version": PHASE_A_VERSION,
            "manifest_classifications": dict(sorted(manifest_classifications.items())),
            "parse_warnings": sorted(warnings, key=lambda item: (item["file"], item["issue"])),
        },
    }
    return record


def discover_repo_dirs(raw_root: Path, repo_filter: list[str] | None) -> list[Path]:
    """Discover raw repository directories, optionally restricted by explicit names."""
    if repo_filter:
        return sorted((raw_root / name for name in repo_filter), key=lambda path: path.name.lower())
    return sorted((path for path in raw_root.iterdir() if path.is_dir()), key=lambda path: path.name.lower())


def build_corpus(raw_root: Path, repo_filter: list[str] | None = None) -> dict[str, Any]:
    """Build the top-level corpus record from a raw code repository root."""
    repos = [build_repo_record(repo_dir) for repo_dir in discover_repo_dirs(raw_root, repo_filter)]
    repos.sort(key=lambda item: (str(item["name"]).lower(), item["repo_id"] or 0))
    return {"schema_version": SCHEMA_VERSION, "repos": repos}


def required_repo_keys() -> set[str]:
    """Return the required top-level keys for every repository record."""
    return {
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


def validate_corpus(corpus: dict[str, Any], raw_root: Path, repo_filter: list[str] | None = None) -> dict[str, Any]:
    """Run the Phase A self-validation checks and return a structured report."""
    repos = corpus.get("repos") or []
    expected_count = len(discover_repo_dirs(raw_root, repo_filter))
    issues: list[str] = []
    direct_manifests = 0
    lock_manifests = 0
    warning_counts: Counter[str] = Counter()
    for repo in repos:
        missing = required_repo_keys() - set(repo)
        if missing:
            issues.append(f"{repo.get('name')}: missing keys {sorted(missing)}")
        for key in ("fork", "archived", "disabled"):
            if not isinstance(repo.get(key), bool):
                issues.append(f"{repo.get('name')}: {key} is not boolean")
        if repo.get("license") is not None and not isinstance(repo["license"].get("is_spdx"), bool):
            issues.append(f"{repo.get('name')}: license.is_spdx is not boolean")
        files = repo.get("files") or {}
        if not isinstance(files.get("has_dockerfile"), bool):
            issues.append(f"{repo.get('name')}: files.has_dockerfile is not boolean")
        if files.get("downloaded_count") != len(files.get("downloaded") or []):
            issues.append(f"{repo.get('name')}: downloaded_count mismatch")
        if files.get("total_count") != sum((files.get("selection_reason_histogram") or {}).values()):
            issues.append(f"{repo.get('name')}: selection_reason_histogram mismatch")
        for dep in (repo.get("dependencies") or []) + (repo.get("repo_dependencies") or []):
            if not isinstance(dep.get("is_vcs"), bool):
                issues.append(f"{repo.get('name')}: dependency is_vcs is not boolean: {dep.get('name')}")
            if not dep.get("sources"):
                issues.append(f"{repo.get('name')}: dependency lacks sources: {dep.get('name')}")
            if dep.get("is_vcs") and not dep.get("vcs_url"):
                issues.append(f"{repo.get('name')}: VCS dependency lacks vcs_url: {dep.get('name')}")
            if not dep.get("is_vcs") and not dep.get("ecosystem"):
                issues.append(f"{repo.get('name')}: package dependency lacks ecosystem: {dep.get('name')}")
            for source in dep.get("sources") or []:
                if not source.get("manifest_path") or not source.get("manifest_scope"):
                    issues.append(f"{repo.get('name')}: dependency source lacks path/scope")
        for identifier in repo.get("identifiers") or []:
            if not identifier.get("source_path"):
                issues.append(f"{repo.get('name')}: identifier lacks source_path")
        citation = repo.get("citation") or {}
        for key in ("present", "placeholder"):
            if not isinstance(citation.get(key), bool):
                issues.append(f"{repo.get('name')}: citation.{key} is not boolean")
        citation_md = repo.get("citation_md")
        if citation_md is not None:
            for key in ("present", "deferred_to_llm"):
                if not isinstance(citation_md.get(key), bool):
                    issues.append(f"{repo.get('name')}: citation_md.{key} is not boolean")
        for author in repo.get("citation", {}).get("software_authors") or []:
            if not any(author.values()):
                issues.append(f"{repo.get('name')}: empty software_author")
        classifications = repo.get("provenance", {}).get("manifest_classifications") or {}
        direct_manifests += sum(1 for value in classifications.values() if value == "direct")
        lock_manifests += sum(1 for value in classifications.values() if value == "lock")
        for env in repo.get("execution_environment") or []:
            if not isinstance(env.get("is_lock"), bool):
                issues.append(f"{repo.get('name')}: execution_environment.is_lock is not boolean: {env.get('source_path')}")
            if env.get("is_lock"):
                source = env.get("source_path")
                if source and any(source in dep_source.get("manifest_path", "") for dep in repo.get("dependencies", []) for dep_source in dep.get("sources", [])):
                    issues.append(f"{repo.get('name')}: lock manifest contributed package deps: {source}")
        for warn in repo.get("provenance", {}).get("parse_warnings") or []:
            warning_counts[warn["issue"]] += 1
    if len(repos) != expected_count:
        issues.append(f"repo count mismatch: expected {expected_count}, got {len(repos)}")
    return {
        "schema_version": corpus.get("schema_version"),
        "repo_count": len(repos),
        "expected_repo_count": expected_count,
        "dependency_count": sum(len(repo.get("dependencies") or []) for repo in repos),
        "repo_dependency_count": sum(len(repo.get("repo_dependencies") or []) for repo in repos),
        "execution_environment_count": sum(len(repo.get("execution_environment") or []) for repo in repos),
        "direct_manifest_count": direct_manifests,
        "lock_manifest_count": lock_manifests,
        "parse_warning_count": sum(warning_counts.values()),
        "parse_warning_counts": dict(sorted(warning_counts.items())),
        "issues": issues,
        "valid": not issues,
    }


def write_json_byte_stable(corpus: dict[str, Any], output_path: Path) -> None:
    """Write the corpus JSON with deterministic formatting and a trailing newline."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(corpus, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def print_report(report: dict[str, Any]) -> None:
    """Print the Phase A validation report to stdout."""
    print("Phase A validation report")
    print(f"schema_version: {report['schema_version']}")
    print(f"repos: {report['repo_count']} / expected {report['expected_repo_count']}")
    print(f"dependencies: {report['dependency_count']}")
    print(f"repo_dependencies: {report['repo_dependency_count']}")
    print(f"execution_environment records: {report['execution_environment_count']}")
    print(f"manifest classifications: direct={report['direct_manifest_count']}, lock={report['lock_manifest_count']}")
    print(f"parse_warnings: {report['parse_warning_count']}")
    for issue, count in report["parse_warning_counts"].items():
        print(f"  {count} x {issue}")
    print(f"valid: {report['valid']}")
    if report["issues"]:
        print("issues:")
        for issue in report["issues"]:
            print(f"  - {issue}")


def main() -> int:
    """Run the corpus builder CLI."""
    args = parse_args()
    corpus = build_corpus(args.raw, args.repos)
    write_json_byte_stable(corpus, args.out)
    report = validate_corpus(corpus, args.raw, args.repos)
    if args.report:
        print_report(report)
    return 0 if report["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
