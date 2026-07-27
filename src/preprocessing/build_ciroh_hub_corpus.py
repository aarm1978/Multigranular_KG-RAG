"""Build the deterministic CIROH Hub Phase A page corpus.

This offline preprocessor converts the materialized Markdown and MDX snapshot in
``data/raw/documents`` into the page-centric Phase A corpus at
``data/interim/documents/ciroh_hub_corpus.json``. It parses and normalizes page
metadata and syntax only; it does not create KG nodes, edges, ontology mappings,
or EvidenceSpan records.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import re
import string
import sys
from collections import Counter
from pathlib import Path, PurePosixPath
from typing import Any, Iterable
from urllib.parse import quote, unquote, urljoin, urlparse

import yaml


SCHEMA_VERSION = "1.0.0"
PHASE_A_VERSION = "1.0.2"
BASE_URL = "https://hub.ciroh.org"
DEFAULT_RAW_ROOT = Path("data/raw/documents")
DEFAULT_OUTPUT = Path("data/interim/documents/ciroh_hub_corpus.json")
SOURCE_GROUPS = ("blog", "docs", "generated_js_page", "release_notes", "src_page")
TITLE_SOURCES = {"front_matter", "first_h1", "description", "path_fallback"}
LINK_TYPES = {"hub_internal", "github", "hydroshare", "doi", "mailto", "anchor", "relative", "other_absolute"}
PAGE_SUFFIXES = {".md", ".mdx"}
EXPLICIT_TRAILING_SLASH_PAGES = {
    "src/pages/community_products/RESOURCES_PAGE_DOCUMENTATION.mdx",
    "src/pages/resources/RESOURCES_PAGE_DOCUMENTATION.mdx",
}
KNOWN_EXCLUSION = {
    "route": "https://hub.ciroh.org/publications",
    "source_path": "src/pages/publications/index.js",
    "reason": "dynamic_zotero_catalog_delegated_to_paper_corpus",
}
WARNING_KEYS = {"file", "issue", "detail"}
PAGE_KEYS = {
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

ATX_HEADING_RE = re.compile(r"^ {0,3}(#{1,6})[ \t]+(.+?)[ \t]*$")
FENCE_RE = re.compile(r"^ {0,3}(`{3,}|~{3,})")
AUTOLINK_RE = re.compile(r"<(https?://[^>]+|mailto:[^>]+)>")
HTML_ANCHOR_RE = re.compile(
    r"<a\b[^>]*?\bhref\s*=\s*([\"'])(.*?)\1[^>]*>(.*?)</a>",
    re.IGNORECASE,
)
MDX_URL_ATTRIBUTE_RE = re.compile(
    r"\b[A-Za-z_:][-A-Za-z0-9_:.]*\s*=\s*([\"'])(https?://[^\"']+)\1"
)
EXTERNAL_COMPONENT_RE = re.compile(r"<(GitHubReadme|GitHubWikiPage)\b(.*?)/?>", re.DOTALL)
QUOTED_PROP_RE = re.compile(r"\b([A-Za-z_][A-Za-z0-9_]*)\s*=\s*([\"'])(.*?)\2", re.DOTALL)
MATERIALIZED_AUTHOR_RE = re.compile(
    r"^\s*-\s+\*\*(.+?)\*\*\s*-\s*(.*?)"
    r"(?:\s+\(\[Profile\]\(([^)]+)\)\))?\s*$"
)


class CorpusBuildError(ValueError):
    """Raised when raw input violates a nonrecoverable Phase A contract rule."""


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse command-line arguments for the Hub corpus builder."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw-root", type=Path, default=DEFAULT_RAW_ROOT, help="Raw CIROH Hub documents root.")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT, help="Output corpus JSON path.")
    parser.add_argument("--expected-page-count", type=int, default=None, help="Optional expected page count.")
    parser.add_argument(
        "--validate-frozen-snapshot",
        action="store_true",
        help="Apply the current 242-page frozen-snapshot acceptance anchors.",
    )
    return parser.parse_args(argv)


def normalize_line_endings(text: str) -> str:
    """Normalize CRLF and CR line endings to LF."""
    return text.replace("\r\n", "\n").replace("\r", "\n")


def sha256_bytes(value: bytes) -> str:
    """Return the lowercase SHA-256 digest of bytes."""
    return hashlib.sha256(value).hexdigest()


def sha256_text(value: str) -> str:
    """Return the SHA-256 digest of UTF-8 text."""
    return sha256_bytes(value.encode("utf-8"))


def sha256_file(path: Path) -> str:
    """Return the SHA-256 digest of exact file bytes."""
    return sha256_bytes(path.read_bytes())


def make_warning(file: str, issue: str, detail: str) -> dict[str, str]:
    """Create a warning record with the contract's stable shape."""
    return {"file": file, "issue": issue, "detail": detail}


def warning_sort_key(item: dict[str, Any]) -> tuple[str, str, str]:
    """Return the deterministic warning sort key."""
    return (str(item.get("file", "")), str(item.get("issue", "")), str(item.get("detail", "")))


def classify_source_group(corpus_path: str) -> str:
    """Classify a candidate page from its raw-root-relative path."""
    if corpus_path.startswith("blog/"):
        return "blog"
    if corpus_path.startswith("release-notes/"):
        return "release_notes"
    if corpus_path.startswith("_generated_js_pages/"):
        return "generated_js_page"
    if corpus_path.startswith("src/pages/"):
        return "src_page"
    if corpus_path.startswith("docs/"):
        return "docs"
    raise CorpusBuildError(f"Unsupported page-bearing path: {corpus_path}")


def exclusion_rule(relative_path: str) -> str | None:
    """Return the generic exclusion category for a raw file, when applicable."""
    path = PurePosixPath(relative_path)
    parts = path.parts
    if "__MACOSX" in parts or path.name == ".DS_Store" or path.name.startswith("._"):
        return "macos_metadata"
    if ".github" in parts:
        return "github_metadata"
    if len(parts) == 1 and path.suffix.lower() in PAGE_SUFFIXES:
        if path.name == "release-notes-template.mdx":
            return "template_document"
        return "root_support_document"
    return None


def discover_candidate_files(raw_root: Path) -> tuple[list[Path], dict[str, int]]:
    """Discover page candidates and aggregate generic exclusions."""
    if not raw_root.is_dir():
        raise CorpusBuildError(f"Raw root does not exist or is not a directory: {raw_root}")
    candidates: list[Path] = []
    exclusions: Counter[str] = Counter(
        {"github_metadata": 0, "macos_metadata": 0, "root_support_document": 0, "template_document": 0}
    )
    for path in sorted((item for item in raw_root.rglob("*") if item.is_file()), key=lambda item: item.relative_to(raw_root).as_posix()):
        relative = path.relative_to(raw_root).as_posix()
        rule = exclusion_rule(relative)
        if rule:
            exclusions[rule] += 1
            continue
        parts = PurePosixPath(relative).parts
        page_bearing = (
            (parts[:1] in (("docs",), ("blog",), ("release-notes",), ("_generated_js_pages",)))
            or parts[:2] == ("src", "pages")
        )
        if page_bearing and path.suffix.lower() in PAGE_SUFFIXES:
            candidates.append(path)
    return candidates, dict(sorted(exclusions.items()))


def json_compatible(value: Any) -> Any:
    """Convert safe-YAML values to deterministic JSON-compatible values."""
    if isinstance(value, dict):
        return {str(key): json_compatible(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_compatible(item) for item in value]
    if isinstance(value, (dt.date, dt.datetime)):
        return value.isoformat()
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    return str(value)


def parse_front_matter(text: str, corpus_path: str) -> tuple[dict[str, Any], str]:
    """Parse required YAML front matter and return it with the normalized body."""
    normalized = normalize_line_endings(text).lstrip("\ufeff")
    lines = normalized.splitlines(keepends=True)
    if not lines or lines[0].rstrip("\n") != "---":
        raise CorpusBuildError(f"{corpus_path}: missing opening YAML front-matter delimiter")
    closing_index = next((index for index, line in enumerate(lines[1:], start=1) if line.rstrip("\n") == "---"), None)
    if closing_index is None:
        raise CorpusBuildError(f"{corpus_path}: missing closing YAML front-matter delimiter")
    yaml_text = "".join(lines[1:closing_index])
    try:
        parsed = yaml.safe_load(yaml_text)
    except yaml.YAMLError as exc:
        raise CorpusBuildError(f"{corpus_path}: invalid YAML front matter: {exc}") from exc
    if parsed is None:
        parsed = {}
    if not isinstance(parsed, dict):
        raise CorpusBuildError(f"{corpus_path}: front matter must be a mapping")
    body = "".join(lines[closing_index + 1 :])
    if body:
        body = body.rstrip("\n") + "\n"
    return json_compatible(parsed), body


def normalize_optional_text(value: Any, field: str, corpus_path: str, warnings: list[dict[str, str]]) -> str | None:
    """Normalize an optional scalar text field, warning for recoverable type coercion."""
    if value is None:
        return None
    if not isinstance(value, str):
        warnings.append(make_warning(corpus_path, "unexpected_front_matter_type", f"{field} normalized from {type(value).__name__}"))
    text = str(value).strip()
    return text or None


def normalize_string_list(value: Any, field: str, corpus_path: str, warnings: list[dict[str, str]]) -> list[str]:
    """Normalize tags or similar metadata to a deterministic string list."""
    if value is None or value == "":
        return []
    values = value if isinstance(value, list) else [value]
    if not isinstance(value, list):
        warnings.append(make_warning(corpus_path, f"non_list_{field}_normalized", f"Scalar {field} converted to a one-item list"))
    normalized = [str(item).strip() for item in values if item is not None and str(item).strip()]
    return sorted(dict.fromkeys(normalized), key=lambda item: (item.casefold(), item))


def normalize_date(value: Any, corpus_path: str, warnings: list[dict[str, str]]) -> tuple[str | None, str | None]:
    """Normalize a front-matter date while preserving its source representation."""
    if value is None or str(value).strip() == "":
        return None, None
    raw = value.isoformat() if isinstance(value, (dt.date, dt.datetime)) else str(value).strip()
    if isinstance(value, dt.datetime):
        return value.date().isoformat(), raw
    if isinstance(value, dt.date):
        return value.isoformat(), raw
    for pattern in ("%m/%d/%Y", "%Y-%m-%d"):
        try:
            return dt.datetime.strptime(raw, pattern).date().isoformat(), raw
        except ValueError:
            pass
    warnings.append(make_warning(corpus_path, "unparseable_last_updated_date", f"Value could not be normalized: {raw}"))
    return None, raw


def mask_characters(characters: list[str], start: int, end: int) -> None:
    """Replace visible characters in a range with spaces while retaining newlines."""
    for index in range(start, end):
        if characters[index] not in {"\n", "\r"}:
            characters[index] = " "


def mask_nonvisible_content(content: str) -> str:
    """Mask fenced code and HTML/MDX comments without changing length or line breaks."""
    characters = list(content)
    fence_char: str | None = None
    fence_length = 0
    comment_end: str | None = None
    offset = 0
    for line in content.splitlines(keepends=True):
        match = FENCE_RE.match(line) if comment_end is None else None
        if fence_char is not None:
            mask_characters(characters, offset, offset + len(line))
            if match and match.group(1)[0] == fence_char and len(match.group(1)) >= fence_length:
                fence_char = None
                fence_length = 0
            offset += len(line)
            continue
        if match:
            token = match.group(1)
            fence_char = token[0]
            fence_length = len(token)
            mask_characters(characters, offset, offset + len(line))
            offset += len(line)
            continue
        cursor = 0
        while cursor < len(line):
            if comment_end is not None:
                closing = line.find(comment_end, cursor)
                if closing < 0:
                    mask_characters(characters, offset + cursor, offset + len(line))
                    cursor = len(line)
                    continue
                closing_end = closing + len(comment_end)
                mask_characters(characters, offset + cursor, offset + closing_end)
                cursor = closing_end
                comment_end = None
                continue
            starts = [
                (position, opener, closer)
                for opener, closer in (("<!--", "-->"), ("{/*", "*/}"))
                if (position := line.find(opener, cursor)) >= 0
            ]
            if not starts:
                break
            position, opener, closer = min(starts, key=lambda item: item[0])
            comment_end = closer
            mask_characters(characters, offset + position, offset + position + len(opener))
            cursor = position + len(opener)
        offset += len(line)
    return "".join(characters)


def mask_html_image_tags(content: str) -> str:
    """Mask complete HTML/MDX ``img`` opening tags while preserving positions."""
    characters = list(content)
    lowered = content.casefold()
    cursor = 0
    while (start := lowered.find("<img", cursor)) >= 0:
        boundary = start + 4
        if boundary < len(content) and not (content[boundary].isspace() or content[boundary] in {"/", ">"}):
            cursor = boundary
            continue
        quote_character: str | None = None
        end = boundary
        while end < len(content):
            character = content[end]
            if quote_character is not None:
                if character == quote_character:
                    quote_character = None
            elif character in {'"', "'"}:
                quote_character = character
            elif character == ">":
                end += 1
                mask_characters(characters, start, end)
                break
            end += 1
        cursor = max(end, boundary)
    return "".join(characters)


def normalize_heading_text(raw_text: str) -> str:
    """Mechanically remove common Markdown wrappers from heading text."""
    text = re.sub(r"[ \t]+#+[ \t]*$", "", raw_text).strip()
    text = re.sub(r"(\*\*|__|~~|`)", "", text)
    text = re.sub(r"(?<!\w)[*_]|[*_](?!\w)", "", text)
    return text.strip()


def extract_headings(content: str) -> list[dict[str, Any]]:
    """Extract visible ATX headings in source order."""
    lines = mask_nonvisible_content(content).splitlines()
    headings: list[dict[str, Any]] = []
    stack: list[dict[str, Any]] = []
    for source_line, line in enumerate(lines, start=1):
        match = ATX_HEADING_RE.match(line)
        if not match:
            continue
        level = len(match.group(1))
        raw_text = re.sub(r"[ \t]+#+[ \t]*$", "", match.group(2)).strip()
        while stack and int(stack[-1]["level"]) >= level:
            stack.pop()
        heading = {
            "ordinal": len(headings) + 1,
            "level": level,
            "text": normalize_heading_text(raw_text),
            "raw_text": raw_text,
            "source_line": source_line,
            "parent_heading_ordinal": stack[-1]["ordinal"] if stack else None,
        }
        headings.append(heading)
        stack.append(heading)
    return headings


def encode_route(route: str, terminal_slash: bool = False) -> str:
    """Normalize and percent-encode a Hub route one segment at a time."""
    stripped = route.strip()
    segments = [segment for segment in stripped.split("/") if segment]
    safe = "!$&'()*+,;=:@-._~"
    encoded = "/".join(quote(unquote(segment), safe=safe) for segment in segments)
    if not encoded:
        return "/"
    result = "/" + encoded
    if terminal_slash:
        result += "/"
    return result


def build_canonical_url(source_group: str, corpus_path: str, raw_path: str | None, slug: str | None) -> str:
    """Construct the canonical Hub URL using source-group-specific rules."""
    if source_group == "blog":
        if not slug:
            raise CorpusBuildError(f"{corpus_path}: blog page is missing slug")
        route = encode_route(f"blog/{slug}")
    elif source_group == "release_notes":
        if not slug:
            raise CorpusBuildError(f"{corpus_path}: release-note page is missing slug")
        route = encode_route(f"release-notes/{slug}")
    else:
        if not raw_path:
            raise CorpusBuildError(f"{corpus_path}: page is missing path")
        is_docs_index = source_group == "docs" and PurePosixPath(corpus_path).stem == "index"
        route_value = raw_path
        terminal_slash = corpus_path in EXPLICIT_TRAILING_SLASH_PAGES
        if is_docs_index and re.search(r"(?:^|/)index/?$", route_value):
            route_value = re.sub(r"(?:^|/)index/?$", "", route_value)
            terminal_slash = True
        route = encode_route(route_value, terminal_slash=terminal_slash)
    canonical = BASE_URL + route
    parsed = urlparse(canonical)
    if parsed.scheme != "https" or parsed.netloc != "hub.ciroh.org":
        raise CorpusBuildError(f"{corpus_path}: canonical URL escapes Hub domain: {canonical}")
    return canonical


def humanize_path_segment(raw_path: str | None, slug: str | None) -> str:
    """Create a conservative title fallback from the last available path segment."""
    source = slug or raw_path or ""
    segments = [segment for segment in source.strip("/").split("/") if segment]
    value = unquote(segments[-1]) if segments else "Home"
    value = re.sub(r"[-_]+", " ", value).strip()
    return value[:1].upper() + value[1:] if value else "Home"


def derive_title(
    front_matter: dict[str, Any],
    headings: list[dict[str, Any]],
    raw_path: str | None,
    slug: str | None,
    corpus_path: str,
    warnings: list[dict[str, str]],
) -> tuple[str, str]:
    """Select a title using the contract's ordered fallback policy."""
    title = front_matter.get("title")
    if title is not None and str(title).strip():
        return str(title).strip(), "front_matter"
    first_h1 = next((heading["text"] for heading in headings if heading["level"] == 1 and heading["text"]), None)
    if first_h1:
        return str(first_h1), "first_h1"
    description = front_matter.get("description")
    if description is not None and str(description).strip():
        return str(description).strip(), "description"
    fallback = humanize_path_segment(raw_path, slug)
    warnings.append(make_warning(corpus_path, "title_from_path_fallback", f"Title derived from path segment: {fallback}"))
    return fallback, "path_fallback"


def normalize_link_target(raw_target: str) -> str:
    """Remove optional angle wrappers and surrounding whitespace from a link target."""
    return raw_target.strip().strip("<>")


def unescape_markdown_punctuation(value: str) -> str:
    """Remove Markdown backslashes only when they escape ASCII punctuation."""
    result: list[str] = []
    index = 0
    while index < len(value):
        if value[index] == "\\" and index + 1 < len(value) and value[index + 1] in string.punctuation:
            result.append(value[index + 1])
            index += 2
        else:
            result.append(value[index])
            index += 1
    return "".join(result)


def is_escaped(value: str, index: int) -> bool:
    """Return whether the character at an index is preceded by an odd backslash run."""
    backslashes = 0
    cursor = index - 1
    while cursor >= 0 and value[cursor] == "\\":
        backslashes += 1
        cursor -= 1
    return backslashes % 2 == 1


def matching_delimiter(value: str, start: int, opener: str, closer: str) -> int | None:
    """Find a balanced closing delimiter while respecting Markdown escapes."""
    depth = 1
    for index in range(start + 1, len(value)):
        if is_escaped(value, index):
            continue
        if value[index] == opener:
            depth += 1
        elif value[index] == closer:
            depth -= 1
            if depth == 0:
                return index
    return None


def markdown_destination(expression: str) -> str | None:
    """Extract the destination from a Markdown parenthesized link expression."""
    value = expression.strip()
    if not value:
        return None
    if value.startswith("<"):
        closing = next(
            (index for index in range(1, len(value)) if value[index] == ">" and not is_escaped(value, index)),
            None,
        )
        return value[1:closing] if closing is not None else None
    depth = 0
    for index, character in enumerate(value):
        if is_escaped(value, index):
            continue
        if character == "(":
            depth += 1
        elif character == ")" and depth:
            depth -= 1
        elif character.isspace() and depth == 0:
            return value[:index]
    return value


def normalize_markdown_anchor(label: str) -> str:
    """Normalize a link label while retaining nested-bracket text and image alt text."""
    result: list[str] = []
    cursor = 0
    while cursor < len(label):
        if label.startswith("![", cursor):
            label_end = matching_delimiter(label, cursor + 1, "[", "]")
            if label_end is not None and label_end + 1 < len(label) and label[label_end + 1] == "(":
                target_end = matching_delimiter(label, label_end + 1, "(", ")")
                if target_end is not None:
                    result.append(label[cursor + 2 : label_end])
                    cursor = target_end + 1
                    continue
        result.append(label[cursor])
        cursor += 1
    return unescape_markdown_punctuation("".join(result))


def scan_markdown_links(line: str) -> list[tuple[int, int, str, str]]:
    """Scan supported inline Markdown links with balanced labels and destinations."""
    records: list[tuple[int, int, str, str]] = []
    cursor = 0
    while cursor < len(line):
        if line[cursor] != "[" or is_escaped(line, cursor):
            cursor += 1
            continue
        if cursor > 0 and line[cursor - 1] == "!" and not is_escaped(line, cursor - 1):
            cursor += 1
            continue
        label_end = matching_delimiter(line, cursor, "[", "]")
        if label_end is None or label_end + 1 >= len(line) or line[label_end + 1] != "(":
            cursor += 1
            continue
        target_end = matching_delimiter(line, label_end + 1, "(", ")")
        if target_end is None:
            cursor += 1
            continue
        target = markdown_destination(line[label_end + 2 : target_end])
        if target:
            label = normalize_markdown_anchor(line[cursor + 1 : label_end])
            records.append((cursor, target_end + 1, label, target))
        cursor = target_end + 1
    return records


def classify_link(raw_target: str) -> str:
    """Classify a link target using the contract's syntactic vocabulary."""
    target = unescape_markdown_punctuation(normalize_link_target(raw_target))
    lowered = target.lower()
    if lowered.startswith("mailto:"):
        return "mailto"
    if target.startswith("#"):
        return "anchor"
    if lowered.startswith("doi:"):
        return "doi"
    parsed = urlparse(target)
    if parsed.scheme in {"http", "https"}:
        host = parsed.netloc.lower().split(":", 1)[0]
        if host == "hub.ciroh.org" or host.endswith(".hub.ciroh.org"):
            return "hub_internal"
        if host in {"github.com", "www.github.com", "raw.githubusercontent.com", "gist.github.com"}:
            return "github"
        if host == "hydroshare.org" or host.endswith(".hydroshare.org"):
            return "hydroshare"
        if host in {"doi.org", "dx.doi.org"}:
            return "doi"
        return "other_absolute"
    if target.startswith("/"):
        return "hub_internal"
    return "relative"


def resolve_link(raw_target: str, canonical_url: str, ambiguous_relative: bool = False) -> str | None:
    """Resolve a syntactic link target when its page-level base is unambiguous."""
    target = unescape_markdown_punctuation(normalize_link_target(raw_target))
    link_type = classify_link(target)
    if link_type in {"github", "hydroshare", "doi", "other_absolute"}:
        return target
    if link_type == "mailto":
        return target
    if link_type == "anchor":
        return canonical_url + target
    if link_type == "hub_internal":
        return urljoin(BASE_URL + "/", target)
    if ambiguous_relative:
        return None
    return urljoin(canonical_url, target)


def nearest_heading_ordinal(headings: list[dict[str, Any]], source_line: int) -> int | None:
    """Return the nearest heading ordinal preceding a source line."""
    preceding = [int(item["ordinal"]) for item in headings if int(item["source_line"]) <= source_line]
    return preceding[-1] if preceding else None


def extract_links(
    content: str,
    canonical_url: str,
    headings: list[dict[str, Any]],
    ambiguous_relative: bool = False,
) -> list[dict[str, Any]]:
    """Extract supported visible link occurrences without syntax overlap duplicates."""
    visible_content = mask_nonvisible_content(content)
    lines = visible_content.splitlines()
    attribute_lines = mask_html_image_tags(visible_content).splitlines()
    links: list[dict[str, Any]] = []
    for source_line, (line, attribute_line) in enumerate(zip(lines, attribute_lines, strict=True), start=1):
        found: list[tuple[int, int, str | None, str]] = []
        occupied: list[tuple[int, int]] = []
        for start, end, anchor, target in scan_markdown_links(line):
            found.append((start, end, anchor, target))
            occupied.append((start, end))
        for match in HTML_ANCHOR_RE.finditer(line):
            if not any(match.start() < end and match.end() > start for start, end in occupied):
                found.append((match.start(), match.end(), re.sub(r"<[^>]+>", "", match.group(3)).strip() or None, match.group(2)))
                occupied.append((match.start(), match.end()))
        for match in AUTOLINK_RE.finditer(line):
            if not any(start <= match.start() < end for start, end in occupied):
                found.append((match.start(), match.end(), match.group(1), match.group(1)))
                occupied.append((match.start(), match.end()))
        for match in MDX_URL_ATTRIBUTE_RE.finditer(attribute_line):
            if not any(start <= match.start() < end for start, end in occupied):
                found.append((match.start(), match.end(), None, match.group(2)))
                occupied.append((match.start(), match.end()))
        for _, _, anchor_text, target in sorted(found, key=lambda item: (item[0], item[1], item[3])):
            raw_target = normalize_link_target(target)
            links.append(
                {
                    "ordinal": len(links) + 1,
                    "anchor_text": anchor_text,
                    "raw_target": raw_target,
                    "resolved_url": resolve_link(raw_target, canonical_url, ambiguous_relative),
                    "link_type": classify_link(raw_target),
                    "source_line": source_line,
                    "heading_ordinal": nearest_heading_ordinal(headings, source_line),
                }
            )
    return links


def extract_external_content_sources(
    content: str,
    corpus_path: str,
    warnings: list[dict[str, str]],
) -> list[dict[str, Any]]:
    """Extract GitHubReadme and GitHubWikiPage declarations without executing MDX."""
    searchable = mask_nonvisible_content(content)
    records: list[dict[str, Any]] = []
    for match in EXTERNAL_COMPONENT_RE.finditer(searchable):
        component = match.group(1)
        props = {item.group(1): item.group(3) for item in QUOTED_PROP_RE.finditer(match.group(2))}
        username = props.get("username")
        repository = props.get("repository") or props.get("repo")
        if component == "GitHubWikiPage":
            source_path = props.get("path")
        else:
            source_path = props.get("path")
            if source_path is None:
                readme_name = props.get("readmeFileName", "README.md")
                subfolder = props.get("subfolder", "").strip("/")
                source_path = f"{subfolder}/{readme_name}" if subfolder and "/" not in readme_name else readme_name
        source_line = searchable.count("\n", 0, match.start()) + 1
        if not username or not repository or (component == "GitHubWikiPage" and not source_path):
            warnings.append(
                make_warning(
                    corpus_path,
                    "malformed_external_content_component",
                    f"{component} at content line {source_line} lacks a required identifying prop",
                )
            )
        records.append(
            {
                "ordinal": len(records) + 1,
                "component": component,
                "username": username,
                "repository": repository,
                "path": source_path,
                "source_line": source_line,
            }
        )
    return records


def extract_materialized_authors(content: str) -> list[dict[str, Any]]:
    """Extract normalized author records from a materialized Authors block."""
    lines = content.splitlines()
    in_authors = False
    records: list[dict[str, Any]] = []
    for line in lines:
        heading = ATX_HEADING_RE.match(line)
        if heading:
            level = len(heading.group(1))
            text = normalize_heading_text(heading.group(2))
            if level == 2 and text.casefold() == "authors":
                in_authors = True
                continue
            if in_authors and level <= 2:
                break
        if not in_authors:
            continue
        match = MATERIALIZED_AUTHOR_RE.match(line)
        if not match:
            continue
        name = match.group(1).strip()
        details = match.group(2).strip()
        profile = match.group(3).strip() if match.group(3) else None
        if "," in details:
            role, affiliation = (part.strip() or None for part in details.split(",", 1))
        else:
            role, affiliation = (details or None), None
        records.append(
            {
                "name": name or None,
                "role": role,
                "affiliation": affiliation,
                "url": profile,
                "source": "materialized_author_block",
            }
        )
    return records


def normalize_authors(
    value: Any,
    content: str,
    corpus_path: str,
    warnings: list[dict[str, str]],
) -> list[dict[str, Any]]:
    """Normalize materialized author details or retain front-matter identifiers."""
    if value is not None and value != "" and not isinstance(value, list):
        warnings.append(make_warning(corpus_path, "non_list_authors_normalized", "Scalar authors value converted to a one-item list"))
    materialized = extract_materialized_authors(content)
    if materialized:
        return materialized
    if value is None or value == "":
        return []
    values = value if isinstance(value, list) else [value]
    records: list[dict[str, Any]] = []
    for item in values:
        if isinstance(item, dict):
            records.append(
                {
                    "name": normalize_author_value(item.get("name")),
                    "role": normalize_author_value(item.get("role")),
                    "affiliation": normalize_author_value(item.get("affiliation")),
                    "url": normalize_author_value(item.get("url")),
                    "source": normalize_author_value(item.get("source")) or "front_matter",
                }
            )
        elif item is not None and str(item).strip():
            records.append(
                {
                    "name": None,
                    "role": None,
                    "affiliation": None,
                    "url": None,
                    "source": "front_matter_identifier",
                    "source_identifier": str(item).strip(),
                }
            )
    return records


def normalize_author_value(value: Any) -> str | None:
    """Normalize one optional author field to trimmed text."""
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def build_page_record(path: Path, raw_root: Path) -> dict[str, Any]:
    """Build one complete Phase A page record from a candidate file."""
    corpus_path = path.relative_to(raw_root).as_posix()
    raw_bytes = path.read_bytes()
    try:
        raw_text = raw_bytes.decode("utf-8-sig")
    except UnicodeDecodeError:
        raw_text = raw_bytes.decode("utf-8", errors="replace")
    front_matter, content = parse_front_matter(raw_text, corpus_path)
    warnings: list[dict[str, str]] = []
    source_group = classify_source_group(corpus_path)
    raw_path = normalize_optional_text(front_matter.get("path"), "path", corpus_path, warnings)
    slug = normalize_optional_text(front_matter.get("slug"), "slug", corpus_path, warnings)
    description = normalize_optional_text(front_matter.get("description"), "description", corpus_path, warnings)
    generated_value = front_matter.get("generated_from_js", False)
    if not isinstance(generated_value, bool):
        warnings.append(make_warning(corpus_path, "unexpected_front_matter_type", "generated_from_js normalized to boolean"))
    generated_from_js = generated_value is True or (isinstance(generated_value, str) and generated_value.strip().casefold() == "true")
    source_path = normalize_optional_text(front_matter.get("source_path"), "source_path", corpus_path, warnings) if generated_from_js else corpus_path
    if generated_from_js and not source_path:
        warnings.append(make_warning(corpus_path, "missing_generated_source_path", "Generated page lacks its original JavaScript source path"))
    canonical_url = build_canonical_url(source_group, corpus_path, raw_path, slug)
    headings = extract_headings(content)
    title, title_source = derive_title(front_matter, headings, raw_path, slug, corpus_path, warnings)
    external_sources = extract_external_content_sources(content, corpus_path, warnings)
    links = extract_links(content, canonical_url, headings, ambiguous_relative=bool(external_sources))
    date_value, date_raw = normalize_date(front_matter.get("Last updated date"), corpus_path, warnings)
    tags = normalize_string_list(front_matter.get("tags"), "tags", corpus_path, warnings)
    authors = normalize_authors(front_matter.get("authors"), content, corpus_path, warnings)
    warnings.sort(key=warning_sort_key)
    return {
        "page_key": f"hub-page:{canonical_url}",
        "canonical_url": canonical_url,
        "path": raw_path,
        "slug": slug,
        "title": title,
        "title_source": title_source,
        "description": description,
        "last_updated_date": date_value,
        "last_updated_date_raw": date_raw,
        "source_group": source_group,
        "corpus_path": corpus_path,
        "source_path": source_path,
        "generated_from_js": generated_from_js,
        "front_matter": front_matter,
        "tags": tags,
        "authors": authors,
        "content_mdx": content,
        "headings": headings,
        "links": links,
        "external_content_sources": external_sources,
        "parent_url": None,
        "file_sha256": sha256_bytes(raw_bytes),
        "content_sha256": sha256_text(content),
        "warnings": warnings,
    }


def parent_candidates(canonical_url: str) -> Iterable[str]:
    """Yield canonical ancestor candidates from nearest to farthest."""
    path = unquote(urlparse(canonical_url).path).rstrip("/")
    parts = [part for part in path.split("/") if part]
    for length in range(len(parts) - 1, 0, -1):
        route = encode_route("/".join(parts[:length]), terminal_slash=True)
        yield BASE_URL + route
        yield (BASE_URL + route).rstrip("/")
    if parts:
        yield BASE_URL + "/"


def resolve_parent_urls(pages: list[dict[str, Any]]) -> None:
    """Assign each page's nearest included canonical ancestor in place."""
    urls = {str(page["canonical_url"]) for page in pages}
    for page in pages:
        canonical = str(page["canonical_url"])
        if canonical == BASE_URL + "/":
            page["parent_url"] = None
            continue
        page["parent_url"] = next((candidate for candidate in parent_candidates(canonical) if candidate in urls), None)


def build_summary(
    pages: list[dict[str, Any]],
    top_level_warnings: list[dict[str, str]],
    exclusions_by_rule: dict[str, int],
) -> dict[str, Any]:
    """Build deterministic summary counts directly from page records."""
    groups = Counter(str(page["source_group"]) for page in pages)
    return {
        "total_pages": len(pages),
        "by_source_group": {group: groups.get(group, 0) for group in SOURCE_GROUPS},
        "generated_from_js": sum(bool(page["generated_from_js"]) for page in pages),
        "with_title_fallback": sum(page["title_source"] != "front_matter" for page in pages),
        "with_tags": sum(bool(page["tags"]) for page in pages),
        "with_authors": sum(bool(page["authors"]) for page in pages),
        "with_external_content": sum(bool(page["external_content_sources"]) for page in pages),
        "total_external_content_sources": sum(len(page["external_content_sources"]) for page in pages),
        "total_headings": sum(len(page["headings"]) for page in pages),
        "total_links": sum(len(page["links"]) for page in pages),
        "with_parent_url": sum(page["parent_url"] is not None for page in pages),
        "page_warning_count": sum(len(page["warnings"]) for page in pages),
        "top_level_warning_count": len(top_level_warnings),
        "exclusions_by_rule": {key: exclusions_by_rule.get(key, 0) for key in sorted(exclusions_by_rule)},
    }


def build_corpus(raw_root: Path) -> dict[str, Any]:
    """Build the complete page-centric Hub Phase A corpus in memory."""
    candidates, exclusions = discover_candidate_files(raw_root)
    pages = [build_page_record(path, raw_root) for path in candidates]
    pages.sort(key=lambda item: (str(item["canonical_url"]), str(item["corpus_path"])))
    canonical_urls = [str(page["canonical_url"]) for page in pages]
    corpus_paths = [str(page["corpus_path"]) for page in pages]
    if len(canonical_urls) != len(set(canonical_urls)):
        duplicates = sorted(key for key, count in Counter(canonical_urls).items() if count > 1)
        raise CorpusBuildError(f"Duplicate canonical URLs: {duplicates}")
    if len(corpus_paths) != len(set(corpus_paths)):
        duplicates = sorted(key for key, count in Counter(corpus_paths).items() if count > 1)
        raise CorpusBuildError(f"Duplicate corpus paths: {duplicates}")
    resolve_parent_urls(pages)
    warnings: list[dict[str, str]] = []
    warnings.sort(key=warning_sort_key)
    return {
        "schema_version": SCHEMA_VERSION,
        "phase_a_version": PHASE_A_VERSION,
        "source": {
            "artifact_type": "ciroh_hub",
            "base_url": BASE_URL,
            "raw_root": "data/raw/documents",
        },
        "pages": pages,
        "known_exclusions": [dict(KNOWN_EXCLUSION)],
        "warnings": warnings,
        "summary": build_summary(pages, warnings, exclusions),
    }


def validate_warning(warning: Any, context: str, issues: list[str]) -> None:
    """Validate one warning record and append actionable issues."""
    if not isinstance(warning, dict) or set(warning) != WARNING_KEYS:
        issues.append(f"{context}: warning does not have required keys")
        return
    if not all(isinstance(warning[key], str) and warning[key] for key in WARNING_KEYS):
        issues.append(f"{context}: warning contains an empty or non-string value")


def validate_page(page: dict[str, Any], raw_root: Path, included_urls: set[str], issues: list[str]) -> None:
    """Validate one page record independently of the build branch."""
    context = str(page.get("corpus_path") or "<unknown page>")
    if set(page) != PAGE_KEYS:
        issues.append(f"{context}: page keys differ from required schema")
    for key in ("page_key", "canonical_url", "title", "corpus_path", "source_path", "file_sha256", "content_sha256"):
        if not isinstance(page.get(key), str) or not page.get(key):
            issues.append(f"{context}: {key} must be a nonempty string")
    if page.get("title_source") not in TITLE_SOURCES:
        issues.append(f"{context}: invalid title_source {page.get('title_source')!r}")
    if page.get("source_group") not in SOURCE_GROUPS:
        issues.append(f"{context}: invalid source_group {page.get('source_group')!r}")
    if not isinstance(page.get("generated_from_js"), bool):
        issues.append(f"{context}: generated_from_js is not boolean")
    for key in ("front_matter",):
        if not isinstance(page.get(key), dict):
            issues.append(f"{context}: {key} is not an object")
    for key in ("tags", "authors", "headings", "links", "external_content_sources", "warnings"):
        if not isinstance(page.get(key), list):
            issues.append(f"{context}: {key} is not an array")
    if not isinstance(page.get("content_mdx"), str):
        issues.append(f"{context}: content_mdx is not a string")
    canonical = str(page.get("canonical_url") or "")
    parsed = urlparse(canonical)
    if parsed.scheme != "https" or parsed.netloc != "hub.ciroh.org":
        issues.append(f"{context}: canonical URL is outside the Hub domain")
    if page.get("page_key") != f"hub-page:{canonical}":
        issues.append(f"{context}: page_key does not match canonical_url")
    parent = page.get("parent_url")
    if parent is not None and parent not in included_urls:
        issues.append(f"{context}: parent_url does not resolve to an included page")
    source_path = str(page.get("corpus_path") or "")
    raw_file = raw_root / source_path
    if not raw_file.is_file():
        issues.append(f"{context}: raw source file is missing")
    else:
        if page.get("file_sha256") != sha256_file(raw_file):
            issues.append(f"{context}: file_sha256 does not match raw bytes")
        try:
            raw_text = raw_file.read_bytes().decode("utf-8-sig")
        except UnicodeDecodeError:
            raw_text = raw_file.read_bytes().decode("utf-8", errors="replace")
        try:
            expected_front_matter, expected_content = parse_front_matter(raw_text, context)
        except CorpusBuildError as exc:
            issues.append(str(exc))
        else:
            if page.get("front_matter") != expected_front_matter:
                issues.append(f"{context}: front_matter does not match raw source")
            if page.get("content_mdx") != expected_content:
                issues.append(f"{context}: content_mdx does not match normalized raw body")
    if page.get("content_sha256") != sha256_text(str(page.get("content_mdx") or "")):
        issues.append(f"{context}: content_sha256 does not match content_mdx")
    content_lines = str(page.get("content_mdx") or "").splitlines()
    heading_ordinals = {heading.get("ordinal") for heading in page.get("headings") or []}
    expected_heading_ordinals = list(range(1, len(page.get("headings") or []) + 1))
    if [heading.get("ordinal") for heading in page.get("headings") or []] != expected_heading_ordinals:
        issues.append(f"{context}: heading ordinals are not deterministic and contiguous")
    for heading in page.get("headings") or []:
        source_line = heading.get("source_line")
        if not isinstance(source_line, int) or source_line < 1 or source_line > len(content_lines):
            issues.append(f"{context}: heading has invalid source_line")
        parent_ordinal = heading.get("parent_heading_ordinal")
        if parent_ordinal is not None and (parent_ordinal not in heading_ordinals or parent_ordinal >= heading.get("ordinal", 0)):
            issues.append(f"{context}: heading has invalid parent_heading_ordinal")
    if [link.get("ordinal") for link in page.get("links") or []] != list(range(1, len(page.get("links") or []) + 1)):
        issues.append(f"{context}: link ordinals are not deterministic and contiguous")
    for link in page.get("links") or []:
        source_line = link.get("source_line")
        if not isinstance(source_line, int) or source_line < 1 or source_line > len(content_lines):
            issues.append(f"{context}: link has invalid source_line")
        if link.get("link_type") not in LINK_TYPES:
            issues.append(f"{context}: link has invalid link_type")
        if link.get("heading_ordinal") is not None and link.get("heading_ordinal") not in heading_ordinals:
            issues.append(f"{context}: link has invalid heading_ordinal")
    if [item.get("ordinal") for item in page.get("external_content_sources") or []] != list(
        range(1, len(page.get("external_content_sources") or []) + 1)
    ):
        issues.append(f"{context}: external-content ordinals are not deterministic and contiguous")
    page_warnings = page.get("warnings") or []
    if page_warnings != sorted(page_warnings, key=warning_sort_key):
        issues.append(f"{context}: page warnings are not sorted")
    for warning in page_warnings:
        validate_warning(warning, context, issues)


def validate_frozen_anchors(corpus: dict[str, Any], issues: list[str]) -> None:
    """Validate acceptance anchors specific to the current frozen raw snapshot."""
    pages = corpus.get("pages") or []
    by_path = {page.get("corpus_path"): page for page in pages}
    if len(pages) != 242:
        issues.append(f"frozen snapshot page count mismatch: expected 242, got {len(pages)}")
    generated = [page for page in pages if page.get("generated_from_js") is True]
    if len(generated) != 11:
        issues.append(f"frozen snapshot generated-page count mismatch: expected 11, got {len(generated)}")
    required_paths = {
        "src/pages/community_products/RESOURCES_PAGE_DOCUMENTATION.mdx",
        "src/pages/resources/RESOURCES_PAGE_DOCUMENTATION.mdx",
    }
    missing = sorted(required_paths - set(by_path))
    if missing:
        issues.append(f"required public resource documentation pages missing: {missing}")
    title_page = by_path.get("docs/services/cloudservices/aws/documentation/data-science-tools/index.mdx")
    if not title_page or title_page.get("title_source") != "first_h1":
        issues.append("AWS Data Science Tools page did not use first_h1 title fallback")
    nwm_page = next((page for page in pages if page.get("path") == "docs/products/data-management/dataaccess/NWMURL Library"), None)
    expected_nwm = "https://hub.ciroh.org/docs/products/data-management/dataaccess/NWMURL%20Library"
    if not nwm_page or nwm_page.get("canonical_url") != expected_nwm:
        issues.append("NWMURL Library canonical URL is incorrect")
    events = by_path.get("_generated_js_pages/events.mdx")
    residue = "getResourceStats(events), [events]); return ("
    if not events or residue in str(events.get("content_mdx") or ""):
        issues.append("Events page contains JavaScript residue; regenerate the raw acquisition snapshot")
    quality_pages = {
        "Home": by_path.get("_generated_js_pages/home.mdx"),
        "Impact": by_path.get("src/pages/impact.mdx"),
    }
    for page_name, page in quality_pages.items():
        page_text = str(page.get("content_mdx") or "") if page else ""
        for platform in ("Aws", "Gcp", "Hpc", "Nsf"):
            section = re.search(rf"\*\*{platform}:\*\*(.*?)(?=\n\*\*[A-Za-z]+:\*\*|\Z)", page_text, re.DOTALL)
            if not section or not all(f"- {key}:" in section.group(1) for key in ("projects", "projectsBar", "users", "usersBar")):
                issues.append(f"{page_name} page does not preserve all semantic keys for {platform.lower()}")


def validate_corpus(
    corpus: dict[str, Any],
    raw_root: Path,
    expected_page_count: int | None = None,
    validate_frozen_snapshot: bool = False,
) -> dict[str, Any]:
    """Validate the complete corpus and return an actionable deterministic report."""
    issues: list[str] = []
    if corpus.get("schema_version") != SCHEMA_VERSION:
        issues.append(f"schema_version must be {SCHEMA_VERSION}")
    if corpus.get("phase_a_version") != PHASE_A_VERSION:
        issues.append(f"phase_a_version must be {PHASE_A_VERSION}")
    pages = corpus.get("pages")
    if not isinstance(pages, list):
        pages = []
        issues.append("pages must be an array")
    try:
        candidates, exclusions = discover_candidate_files(raw_root)
    except CorpusBuildError as exc:
        candidates, exclusions = [], {}
        issues.append(str(exc))
    expected_paths = sorted(path.relative_to(raw_root).as_posix() for path in candidates)
    actual_paths = [str(page.get("corpus_path") or "") for page in pages]
    if sorted(actual_paths) != expected_paths:
        issues.append("page membership does not exactly match discovered candidates")
    canonical_urls = [str(page.get("canonical_url") or "") for page in pages]
    if len(canonical_urls) != len(set(canonical_urls)):
        issues.append("canonical URLs are not unique")
    if len(actual_paths) != len(set(actual_paths)):
        issues.append("corpus paths are not unique")
    expected_order = sorted(pages, key=lambda item: (str(item.get("canonical_url", "")), str(item.get("corpus_path", ""))))
    if pages != expected_order:
        issues.append("pages are not sorted by canonical_url and corpus_path")
    included_urls = set(canonical_urls)
    for page in pages:
        validate_page(page, raw_root, included_urls, issues)
        path = str(page.get("corpus_path") or "")
        if exclusion_rule(path) is not None:
            issues.append(f"excluded artifact was emitted as a page: {path}")
        try:
            expected_canonical = build_canonical_url(
                str(page.get("source_group")),
                path,
                page.get("path"),
                page.get("slug"),
            )
        except CorpusBuildError as exc:
            issues.append(str(exc))
        else:
            if page.get("canonical_url") != expected_canonical:
                issues.append(f"{path}: canonical_url does not follow its source-group rule")
        content = str(page.get("content_mdx") or "")
        expected_headings = extract_headings(content)
        if page.get("headings") != expected_headings:
            issues.append(f"{path}: headings do not match deterministic extraction")
        component_warnings: list[dict[str, str]] = []
        expected_external = extract_external_content_sources(content, path, component_warnings)
        if page.get("external_content_sources") != expected_external:
            issues.append(f"{path}: external_content_sources do not match deterministic extraction")
        expected_links = extract_links(
            content,
            str(page.get("canonical_url") or ""),
            expected_headings,
            ambiguous_relative=bool(expected_external),
        )
        if page.get("links") != expected_links:
            issues.append(f"{path}: links do not match deterministic extraction")
    expected_parent_records = [{"canonical_url": url, "parent_url": None} for url in canonical_urls]
    resolve_parent_urls(expected_parent_records)
    expected_parents = {record["canonical_url"]: record["parent_url"] for record in expected_parent_records}
    for page in pages:
        if page.get("parent_url") != expected_parents.get(page.get("canonical_url")):
            issues.append(f"{page.get('corpus_path')}: parent_url is not the nearest included canonical ancestor")
    exclusions_records = corpus.get("known_exclusions") or []
    if KNOWN_EXCLUSION not in exclusions_records:
        issues.append("/publications methodological exclusion is missing")
    if BASE_URL + "/publications" in included_urls or BASE_URL + "/publications/" in included_urls:
        issues.append("/publications must not be emitted as a Hub page")
    top_warnings = corpus.get("warnings") or []
    if top_warnings != sorted(top_warnings, key=warning_sort_key):
        issues.append("top-level warnings are not sorted")
    for warning in top_warnings:
        validate_warning(warning, "top-level", issues)
    expected_summary = build_summary(pages, top_warnings, exclusions)
    if corpus.get("summary") != expected_summary:
        issues.append("summary does not reconcile with pages, warnings, and exclusions")
    if expected_page_count is not None and len(pages) != expected_page_count:
        issues.append(f"page count mismatch: expected {expected_page_count}, got {len(pages)}")
    if validate_frozen_snapshot:
        validate_frozen_anchors(corpus, issues)
    issue_list = sorted(dict.fromkeys(issues))
    return {
        "schema_version": corpus.get("schema_version"),
        "phase_a_version": corpus.get("phase_a_version"),
        "candidate_file_count": len(candidates),
        "page_count": len(pages),
        "exclusions_by_rule": expected_summary["exclusions_by_rule"],
        "by_source_group": expected_summary["by_source_group"],
        "generated_from_js": expected_summary["generated_from_js"],
        "with_title_fallback": expected_summary["with_title_fallback"],
        "total_headings": expected_summary["total_headings"],
        "total_links": expected_summary["total_links"],
        "total_external_content_sources": expected_summary["total_external_content_sources"],
        "warning_count": expected_summary["page_warning_count"] + expected_summary["top_level_warning_count"],
        "warning_counts": dict(
            sorted(
                Counter(
                    warning["issue"]
                    for page in pages
                    for warning in page.get("warnings") or []
                    if isinstance(warning, dict) and "issue" in warning
                ).items()
            )
        ),
        "issues": issue_list,
        "valid": not issue_list,
    }


def serialize_corpus(corpus: dict[str, Any]) -> bytes:
    """Serialize a corpus with stable formatting and one terminal newline."""
    return (json.dumps(corpus, indent=2, ensure_ascii=False, sort_keys=True) + "\n").encode("utf-8")


def write_deterministic_json(corpus: dict[str, Any], output_path: Path) -> str:
    """Write deterministic UTF-8 JSON and return its SHA-256 digest."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    payload = serialize_corpus(corpus)
    output_path.write_bytes(payload)
    return sha256_bytes(payload)


def print_report(report: dict[str, Any], output_path: Path, output_sha256: str | None = None) -> None:
    """Print the concise deterministic Phase A build and validation report."""
    print("CIROH Hub Phase A validation report")
    print(f"schema_version: {report['schema_version']}")
    print(f"phase_a_version: {report['phase_a_version']}")
    print(f"candidate files discovered: {report['candidate_file_count']}")
    print(f"pages included: {report['page_count']}")
    print("files excluded by category:")
    for key, value in report["exclusions_by_rule"].items():
        print(f"  {key}: {value}")
    print("source-group counts:")
    for key, value in report["by_source_group"].items():
        print(f"  {key}: {value}")
    print(f"generated-from-JS pages: {report['generated_from_js']}")
    print(f"title fallback pages: {report['with_title_fallback']}")
    print(f"headings: {report['total_headings']}")
    print(f"links: {report['total_links']}")
    print(f"external content sources: {report['total_external_content_sources']}")
    print(f"warnings: {report['warning_count']}")
    for issue, count in report["warning_counts"].items():
        print(f"  {issue}: {count}")
    print(f"valid: {report['valid']}")
    if report["issues"]:
        print("issues:")
        for issue in report["issues"]:
            print(f"  - {issue}")
    print(f"output path: {output_path.as_posix()}")
    print(f"output SHA-256: {output_sha256 or 'not written'}")


def main(argv: list[str] | None = None) -> int:
    """Run the complete offline Hub Phase A build, validation, and write flow."""
    args = parse_args(argv)
    try:
        corpus = build_corpus(args.raw_root)
        report = validate_corpus(
            corpus,
            args.raw_root,
            expected_page_count=args.expected_page_count,
            validate_frozen_snapshot=args.validate_frozen_snapshot,
        )
    except CorpusBuildError as exc:
        print(f"CIROH Hub Phase A build failed: {exc}", file=sys.stderr)
        return 1
    if not report["valid"]:
        print_report(report, args.output)
        return 1
    output_sha256 = write_deterministic_json(corpus, args.output)
    print_report(report, args.output, output_sha256)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
