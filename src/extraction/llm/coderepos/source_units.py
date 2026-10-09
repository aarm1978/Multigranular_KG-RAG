"""Bounded offline GitHub reader for frozen Step 11 v0.3 §§2 and 4.

Read only supplied Phase A records and manifest-selected files under an explicit
raw corpus root. Returned authorities preserve full text; units are conservative
prose passages, not semantic assertions or proof of target eligibility. Ambiguous
content is held for review. No network, execution, graph or Publication pipeline.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path, PurePosixPath
import re
from typing import Any, Mapping
from urllib.parse import quote


CONTRACT_ID = "study2-step11-semantic-contracts/v0.3"
REASONS = frozenset({"allowed_exact_filename", "allowed_path_prefix",
                     "allowed_semantic_folder", "allowed_top_level_doc",
                     "allowed_top_level_notebook"})
TEXT_EXTENSIONS = frozenset({".md", ".markdown", ".rst", ".txt"})
DECODE_POLICY = "utf-8-sig-else-latin-1; CRLF/CR-to-LF; strip-leading-BOM"
ADMIN_NAME = re.compile(r"^(license|licence|copying|security|code_of_conduct|requirements)(?:[._-]|$)", re.I)
ADMIN_PROSE = re.compile(r"\b(pull requests?|code of conduct|copyright|all rights reserved|"
                         r"report (?:a |an )?(?:bug|vulnerability)|contributor license)\b", re.I)


def _sha(raw: bytes) -> str:
    """Hash exact bytes without asserting acquisition verification."""
    return hashlib.sha256(raw).hexdigest()


def _safe_path(value: Any) -> bool:
    """Require an unchanged, unambiguous relative POSIX path."""
    return (isinstance(value, str) and bool(value) and not value.startswith("/")
            and not re.search(r"[\\\x00-\x1f:]", value)
            and all(part not in {"", ".", ".."} for part in value.split("/")))


def _decode(raw: bytes) -> str:
    """Apply the existing Phase A text-reader policy, preserving its authority."""
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        text = raw.decode("latin-1")
    return text.replace("\r\n", "\n").replace("\r", "\n").lstrip("\ufeff")


def _line(text: str, offset: int) -> int:
    """Count original CRLF, CR and LF lines at a Unicode-code-point offset."""
    return 1 + sum(m.end() <= offset for m in re.finditer(r"\r\n|\r|\n", text))


def _passages(text: str) -> tuple[list[tuple[int, int, str | None]], bool]:
    """Select plain prose runs without rewriting their text or coordinates.

    Fences, indented blocks, directives, HTML, comments, link/badge-only lines,
    shell/code/configuration lines and administrative passages are not units.
    Unknown markup and short/uncertain content require review. This is a bounded
    structural selector, not a scientific relevance or semantic target classifier.
    """
    spans: list[tuple[int, int, str | None]] = []
    start: int | None = None
    end = offset = 0
    heading = None
    fence: str | None = None
    comment = False
    review = False

    def flush() -> None:
        """Retain a contiguous literal passage under its original heading."""
        nonlocal start
        if start is not None:
            spans.append((start, end, heading))
            start = None

    for line in text.splitlines(keepends=True):
        stripped = line.strip()
        marker = re.match(r"^\s{0,3}(`{3,}|~{3,})", line)
        title = re.match(r"^ {0,3}#{1,6}\s+(.+?)\s*$", line)
        if fence is not None or marker:
            flush()
            if fence is None:
                fence = marker.group(1)
            elif marker and marker.group(1)[0] == fence[0] and len(marker.group(1)) >= len(fence):
                fence = None
        elif comment or "<!--" in line or "{/*" in line:
            flush()
            comment = not ("-->" in line or "*/}" in line)
        elif title:
            flush()
            heading = title.group(1)
        elif not stripped:
            flush()
        elif (line.startswith(("    ", "\t")) or stripped.startswith((".. ", "<", "{", "!", "$", ">"))
              or re.match(r"^(?:import |from \S+ import |def |class |#!|[\w.-]+\s*[:=]|[-=~]{3,}$)", stripped)
              or ADMIN_PROSE.search(line)):
            flush()
            review = True
        else:
            visible = re.sub(r"!?\[[^\]]*\]\([^)]*\)|https?://\S+|`[^`]*`", "", stripped)
            if len(re.findall(r"[^\W\d_]+", visible)) < 3:
                flush()
                review = True
            else:
                if start is None:
                    start = offset
                end = offset + len(line)
        offset += len(line)
    flush()
    return spans, review or fence is not None or comment


def read_repository_sources(
    repo: Mapping[str, Any], raw_corpus_root: Path, *,
    trusted_raw_sha256: Mapping[str, str] | None = None,
    trusted_authority_sha256: Mapping[tuple[str, int | None], str] | None = None,
) -> dict[str, Any]:
    """Read one caller-supplied Phase A repo, never scan the raw corpus.

    Raw paths resolve as ``root / repo['name'] / 'contents' / manifest_path``.
    Trusted optional text digests are keyed by (original path, Markdown cell index
    or None); raw digests by original path. Self-computed hashes are labeled as
    such. Phase A README text is never re-decoded or checked against raw bytes.
    Unknown acquisition reasons/content remain review diagnostics, not absence.
    ``inputComplete`` covers this bounded reader only, not semantic extraction.
    """
    result: dict[str, Any] = {"authorities": [], "sourceUnits": [], "reads": [],
                              "diagnostics": [], "inputComplete": True}
    archive = repo.get("archive")
    sha = archive.get("frozen_commit_sha") if isinstance(archive, Mapping) else None
    name, full_name, repo_id = repo.get("name"), repo.get("full_name"), repo.get("repo_id")
    context = {"artifactFamily": "github", "repo_id": repo_id, "full_name": full_name,
               "frozenCommitSha": sha, "contractID": CONTRACT_ID}

    def record(status: str, reason: str, **extra: Any) -> None:
        """Keep source-specific read decisions and failures distinct."""
        row = {**context, **extra, "status": status, "reason": reason}
        result["reads"].append(row)
        if status in {"failed_source_or_evidence_binding", "needs_review"}:
            result["diagnostics"].append(dict(row))
            result["inputComplete"] = False

    def failed(reason: str, **extra: Any) -> None:
        """Record a technical source failure without semantic abstention."""
        record("failed_source_or_evidence_binding", reason, **extra)

    if (type(repo_id) is not int or not _safe_path(name) or "/" in name
            or not _safe_path(full_name) or len(full_name.split("/")) != 2
            or not isinstance(sha, str) or re.fullmatch(r"[0-9a-fA-F]{40}", sha) is None):
        failed("source_provenance_missing_or_malformed")
        return result
    context["canonicalArtifactID"] = f"github:repo:{repo_id}"
    root = Path(raw_corpus_root).resolve()
    contents = root / name / "contents"

    def digest_matches(actual: str, expected: Any) -> bool:
        """Accept only exact trusted SHA-256 matches, never repair a digest."""
        return isinstance(expected, str) and re.fullmatch(r"[0-9a-f]{64}", expected) is not None and actual == expected

    def authority(text: str, meta: dict[str, Any], cell: int | None = None) -> None:
        """Record exact full authority and select original bounded prose spans."""
        try:
            digest = _sha(text.encode("utf-8"))
        except UnicodeEncodeError:
            failed("source_text_malformed", **meta, cellIndex=cell)
            return
        if any(ord(c) < 32 and c not in "\t\r\n" for c in text):
            failed("source_text_malformed", **meta, cellIndex=cell)
            return
        key = (meta["path"], cell)
        expected = trusted_authority_sha256 or {}
        if key in expected and not digest_matches(digest, expected[key]):
            failed("source_content_integrity_failure", **meta, cellIndex=cell)
            return
        base = {**context, **meta, "cellIndex": cell, "authorityTextSha256": digest,
                "textIntegrityStatus": "matched_trusted_digest" if key in expected else "computed_only",
                "sourceLocation": f"https://github.com/{full_name}/blob/{sha}/{quote(meta['path'], safe='/')}"}
        result["authorities"].append({**base, "text": text})
        record("source_read_success", "authority_recorded", **meta, cellIndex=cell)
        spans, review = _passages(text)
        # These files need purpose-specific passage review before semantic use.
        special = PurePosixPath(meta["path"]).name.lower().startswith(("contributing", "changelog"))
        if special:
            spans = []
            review = True
        for start, end, heading in spans:
            identity = json.dumps([repo_id, full_name, sha, meta["path"], cell, digest, start, end],
                                  separators=(",", ":"), ensure_ascii=True)
            result["sourceUnits"].append({
                **base, "sourceUnitID": "github:unit:" + _sha(identity.encode()),
                "text": text[start:end], "startOffsetInAuthority": start,
                "endOffsetInAuthority": end, "startLine": _line(text, start),
                "endLine": _line(text, end - 1), "headingContext": heading,
                "contentKind": "prose", "eligibility": "prose_candidate",
            })
        if review:
            record("needs_review", "content_kind_or_purpose_requires_review", **meta, cellIndex=cell)

    readme = repo.get("readme") or {}
    if not isinstance(readme, Mapping):
        failed("phase_a_readme_malformed")
        readme = {}
    readme_path, readme_text = readme.get("source_path"), readme.get("text")
    # A malformed present Phase A authority also must not silently fall back.
    reserved_readme = readme_path if readme_text is not None else None
    if readme_text is not None:
        if not _safe_path(readme_path) or not PurePosixPath(readme_path).name.lower().startswith("readme"):
            failed("phase_a_readme_path_invalid", path=readme_path)
        elif PurePosixPath(readme_path).suffix.lower() not in TEXT_EXTENSIONS | {""}:
            record("excluded", "non_prose_file_type", path=readme_path)
        elif not isinstance(readme_text, str):
            failed("phase_a_readme_malformed", path=readme_path)
        else:
            authority(readme_text, {"path": readme_path, "authorityKind": "phase_a_readme",
                                   "decodePolicy": "unchanged Phase A readme.text"})
    elif readme.get("present") is True:
        failed("phase_a_readme_text_missing", path=readme_path)
        reserved_readme = readme_path

    files = repo.get("files")
    entries = files.get("downloaded") if isinstance(files, Mapping) else None
    if not isinstance(entries, list):
        failed("download_manifest_missing_or_malformed")
        return result
    seen: dict[str, Mapping[str, Any]] = {}
    for entry in entries:
        if not isinstance(entry, Mapping):
            failed("download_manifest_entry_malformed")
            continue
        path = entry.get("path")
        meta = {key: entry.get(key) for key in ("path", "selection_reason", "file_role", "extension")}
        if entry.get("downloaded") is False:
            record("excluded", "not_downloaded", **meta)
            continue
        if entry.get("downloaded") is not True:
            failed("download_status_missing_or_malformed", **meta)
            continue
        if not _safe_path(path):
            failed("unsafe_source_path", **meta)
            continue
        if path == reserved_readme:
            record("skipped_duplicate", "phase_a_readme_authority", **meta)
            continue
        if path in seen:
            if entry != seen[path]:
                failed("conflicting_manifest_entries", **meta)
            else:
                record("skipped_duplicate", "duplicate_manifest_path", **meta)
            continue
        seen[path] = entry
        if entry.get("selection_reason") not in REASONS:
            record("needs_review", "unrecognized_selection_reason", **meta)
            continue
        suffix = PurePosixPath(path).suffix.lower()
        filename = PurePosixPath(path).name.lower()
        if suffix not in TEXT_EXTENSIONS | {".ipynb"} and not (not suffix and filename in {"readme", "citation"}):
            record("excluded", "non_prose_file_type", **meta)
            continue
        if ADMIN_NAME.match(filename) or any(part.lower() in {".github", ".git"} for part in path.split("/")):
            record("excluded", "administrative_or_machine_file", **meta)
            continue
        declared = entry.get("extension")
        if not isinstance(declared, str) or declared.lower() != suffix:
            record("needs_review", "extension_metadata_mismatch", **meta)
            continue
        try:
            resolved_contents = contents.resolve()
            resolved = (contents / path).resolve()
            if not resolved_contents.is_relative_to(root) or not resolved.is_relative_to(resolved_contents):
                failed("unsafe_source_path", **meta)
                continue
            raw = resolved.read_bytes()
        except FileNotFoundError:
            failed("downloaded_file_missing", **meta)
            continue
        except (OSError, RuntimeError):
            failed("downloaded_file_unreadable", **meta)
            continue
        raw_hash = _sha(raw)
        expected_raw = trusted_raw_sha256 or {}
        if path in expected_raw and not digest_matches(raw_hash, expected_raw[path]):
            failed("source_content_integrity_failure", **meta, rawFileSha256=raw_hash)
            continue
        meta.update({"rawFileSha256": raw_hash, "authorityKind": "downloaded_file",
                     "rawIntegrityStatus": "matched_trusted_digest" if path in expected_raw else "computed_only"})
        if suffix != ".ipynb":
            authority(_decode(raw), {**meta, "decodePolicy": DECODE_POLICY})
            continue
        try:
            notebook = json.loads(raw.decode("utf-8-sig"))
            if not isinstance(notebook, dict) or not isinstance(notebook.get("cells"), list):
                raise ValueError("Notebook cells must be an array")
        except (UnicodeError, ValueError):
            failed("downloaded_notebook_malformed", **meta)
            continue
        record("source_read_success", "notebook_json_read", **meta)
        for index, cell in enumerate(notebook["cells"]):
            if not isinstance(cell, dict) or not isinstance(cell.get("cell_type"), str):
                failed("notebook_cell_malformed", **meta, cellIndex=index)
                continue
            if cell["cell_type"] != "markdown":
                continue
            source = cell.get("source")
            if isinstance(source, list) and all(isinstance(part, str) for part in source):
                source = "".join(source)
            if not isinstance(source, str):
                failed("notebook_markdown_source_malformed", **meta, cellIndex=index)
                continue
            authority(source, {**meta, "decodePolicy": "original JSON Markdown source; ordered fragment join"}, index)
    return result
