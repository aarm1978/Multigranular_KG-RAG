"""Deterministic, source-preserving Publication Pilot 1 source-unit construction.

The module reads canonical Markdown paths from the frozen Phase A corpus.  It never
uses network services, invokes an LLM, or mutates an upstream artifact.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
import hashlib
import html
import json
import os
from pathlib import Path
import re
import tempfile
from typing import Any, Iterable, Mapping, Sequence


CONTRACT_VERSION = "0.1.1"
CONTRACT_HASH = "31fbd6c76e0efbccdde3e6945191e2a174f19565711b11aedc27d4d63e8e1c3a"
BUILDER_VERSION = "0.1.4"
TARGET_INVENTORY_VERSION = "0.1.0"
TARGET_INVENTORY_HASH = "3d8a80c4ff8794588e2551e63a61e72c60a9afcb89d8b7a7058ff23e25ee4760"
ONTOLOGY_VERSION = "0.1.3"
ONTOLOGY_OWL_HASH = "ecfcd7058b3404dd1a02875654cc8c7f905e20bdf2e559b4498aa2e7d0f12a57"
PHASE_B_VERSION = "1.0.2"
PHASE_B_HASH = "675049dae5c3dfed6f492ad0aa79e27fc1a9b37d0ecbc13ab3cf1a69cdb8efaf"
PREFERRED_MAX = 10_000
ATOMIC_HARD_MAX = 20_000
PILOT_ARTIFACT_IDS = ("10", "15", "16", "18", "34", "37", "46", "54", "79", "276", "87", "87-corrigendum")
CONTENT_TYPES = {"heading", "prose", "list", "table", "caption", "equation", "code", "blockquote", "html", "metadata", "mixed"}
ELIGIBILITIES = {"eligible", "context_only", "excluded", "needs_review"}
SECTION_ROLES = {"front_matter", "abstract", "highlights", "introduction", "background", "related_work", "study_area", "data", "methods", "results", "discussion", "limitations", "conclusion", "future_work", "appendix", "acknowledgments", "author_contributions", "data_availability", "references", "other"}
HEADING_RE = re.compile(r"^ {0,3}(#{1,6})[ \t]+(.+?)[ \t]*#*[ \t]*$")
FENCE_RE = re.compile(r"^ {0,3}(`{3,}|~{3,})(.*)$")
LIST_RE = re.compile(r"^ {0,3}(?:[-+*]|\d+[.)])[ \t]+")
CAPTION_RE = re.compile(r"^\s*(?:\*\*)?(?:figure|fig\.?|table)\s+[\w.-]+\s*[:.]", re.I)
REFERENCE_RE = re.compile(r"^(?:references?|bibliography|literature cited|works cited|reference list)$")
REFERENCE_RESET_RE = re.compile(r"^(?:appendix|supplementary material|supporting information)(?:\b|$)")
HASH_RE = re.compile(r"^[0-9a-f]{64}$")
MARKDOWN_IMAGE_RE = re.compile(r"!\[[^\]]*\]\([^\n)]*(?:\([^\n)]*\)[^\n)]*)*\)")
HTML_IMAGE_RE = re.compile(r"<img\b[^>]*>", re.IGNORECASE)
HTML_CONTAINER_RE = re.compile(r"^\s*<(div|section|article|aside|table|figure|details|blockquote)\b", re.IGNORECASE)
PAGE_ANCHOR_TOKEN_PATTERN = r"(?:<!--\s*page\b.*?-->)|(?:<span\s+id=[\"']page-[^\"']+[\"']\s*></span>)"
PAGE_ANCHOR_TOKEN_RE = re.compile(PAGE_ANCHOR_TOKEN_PATTERN, re.IGNORECASE)
PAGE_ANCHOR_PREFIX_RE = re.compile(rf"^[ \t]*(?:{PAGE_ANCHOR_TOKEN_PATTERN})+", re.IGNORECASE)
TABLE_QUALITY_ORDER = {"well_formed": 0, "partially_recoverable": 1, "broken": 2}
STABLE_ERROR_CODES = (
    "SOURCE_FILE_NOT_FOUND", "SOURCE_PATH_MISMATCH", "INVALID_UTF8",
    "RAW_FILE_HASH_MISMATCH", "CANONICAL_TEXT_HASH_MISMATCH",
    "FORBIDDEN_CONTROL_CHARACTER_UNSANITIZED", "SECTION_PARTITION_GAP",
    "SECTION_PARTITION_OVERLAP", "UNIT_PARTITION_GAP", "UNIT_PARTITION_OVERLAP",
    "UNIT_OUTSIDE_SECTION", "UNIT_TEXT_MISMATCH", "OFFSET_MISMATCH",
    "LINE_RANGE_MISMATCH", "TEXT_HASH_MISMATCH", "INPUT_HASH_MISMATCH",
    "UNKNOWN_SECTION_ROLE", "UNKNOWN_CONTENT_TYPE", "UNKNOWN_ELIGIBILITY",
    "UNKNOWN_ROUTING_CATEGORY", "UNKNOWN_OPERATIONAL_TARGET",
    "OUT_OF_SCOPE_TARGET_ROUTED", "ABSTRACT_TARGET_ROUTED",
    "REFERENCE_SCOPE_AMBIGUOUS", "OVERSIZE_ATOMIC_BLOCK", "BROKEN_TABLE_STRUCTURE",
)
REQUIRED_SOURCE_UNIT_FIELDS = frozenset({
    "contractVersion", "paperID", "canonicalArtifactID", "recordType",
    "phaseASchemaVersion", "phaseAVersion", "sourceFile", "rawFileSha256",
    "canonicalTextSha256", "sourceUnitID", "sectionID", "sectionOrdinal",
    "sectionLevel", "sectionTitleRaw", "sectionTitleNormalized", "sectionPath",
    "sectionRole", "sectionRoleRule", "chunkNumber", "contentTypes", "eligibility",
    "exclusionReasons", "text", "sectionStartOffsetInDocument",
    "sectionEndOffsetInDocument", "startOffsetInDocument", "endOffsetInDocument",
    "startOffsetInSection", "endOffsetInSection", "startLine", "endLine", "textHash",
    "inputHash", "markerBlockRefs", "pageRefs", "deterministicNodeRefs",
    "deterministicEdgeRefs", "deferredRecordRefs", "eligibleCategories",
    "eligibleOperationalTargetIDs", "adjacentUnitRefs", "characterCount",
    "atomicBlockCount", "blockMetadata", "tableQuality", "requestEligible",
    "validationResults", "reviewRequired", "reviewReasons",
})


class SourceUnitError(ValueError):
    """Report a deterministic contract or input validation failure."""


@dataclass(frozen=True)
class Span:
    """Represent one exact half-open source span and its block classification."""

    start: int
    end: int
    kind: str
    table_quality: str | None = None
    split_from_oversize: bool = False
    needs_review: bool = False
    review_reason: str | None = None
    visual_only: bool = False
    contains_visual: bool = False


def sha256_bytes(value: bytes) -> str:
    """Return a lowercase SHA-256 hexadecimal digest."""

    return hashlib.sha256(value).hexdigest()


def canonical_json(value: Any) -> bytes:
    """Serialize a value as compact canonical UTF-8 JSON."""

    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def normalize_canonical_text(raw: bytes) -> str:
    """Apply exactly the frozen BOM, newline, and forbidden-control policy."""

    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise SourceUnitError(f"INVALID_UTF8: {exc}") from exc
    if text.startswith("\ufeff"):
        text = text[1:]
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    return "".join(" " if ord(character) < 32 and character not in "\t\n" else character for character in text)


def _line_spans(text: str) -> list[tuple[int, int, str]]:
    """Return exact offsets and newline-stripped values for every source line."""

    spans: list[tuple[int, int, str]] = []
    offset = 0
    for line in text.splitlines(keepends=True):
        end = offset + len(line)
        spans.append((offset, end, line[:-1] if line.endswith("\n") else line))
        offset = end
    if offset < len(text) or not spans:
        spans.append((offset, len(text), text[offset:]))
    return spans


def _block_line_spans(text: str) -> list[tuple[int, int, str]]:
    """Split only leading page-anchor prefixes from their physical source lines."""

    spans: list[tuple[int, int, str]] = []
    for start, end, line in _line_spans(text):
        match = PAGE_ANCHOR_PREFIX_RE.match(line)
        if not match:
            spans.append((start, end, line))
            continue
        split = start + match.end()
        spans.append((start, split, match.group(0)))
        if split < end:
            spans.append((split, end, line[match.end():]))
    return spans


def recognized_headings(text: str) -> list[dict[str, Any]]:
    """Recognize ATX headings outside Markdown fenced code blocks."""

    headings: list[dict[str, Any]] = []
    fence_character: str | None = None
    fence_length = 0
    for start, end, line in _line_spans(text):
        fence = FENCE_RE.match(line)
        if fence:
            marker = fence.group(1)
            if fence_character is None:
                fence_character, fence_length = marker[0], len(marker)
            elif marker[0] == fence_character and len(marker) >= fence_length and not fence.group(2).strip():
                fence_character, fence_length = None, 0
            continue
        if fence_character is None:
            match = HEADING_RE.match(line)
            if match:
                headings.append({"start": start, "end": end, "level": len(match.group(1)), "raw": match.group(2)})
    return headings


def normalize_section_title(value: str) -> str:
    """Create the contract's routing-only normalized heading title."""

    value = html.unescape(re.sub(r"<[^>]+>", " ", value))
    value = re.sub(r"!?(?:\[([^]]*)\])\([^)]*\)", r"\1", value)
    value = re.sub(r"[*_~`]", "", value)
    return " ".join(value.split()).casefold()


def assign_section_role(title: str | None) -> tuple[str, str]:
    """Assign one frozen routing role with an auditable deterministic rule."""

    if title is None:
        return "front_matter", "synthetic_front_matter"
    patterns = (
        ("references", r"^(?:references?|bibliography|literature cited|works cited|reference list)$"),
        ("abstract", r"^(?:\d+(?:\.\d+)*[ .-]+)?abstract$"),
        ("highlights", r"\b(?:highlights?|key points?)\b"),
        ("introduction", r"\bintroduction\b"), ("background", r"\bbackground\b"),
        ("related_work", r"\b(?:related work|literature review)\b"),
        ("study_area", r"\b(?:study area|study site)\b"),
        ("data_availability", r"\b(?:data|code|software) availability\b|availability statement"),
        ("data", r"^(?:\d+(?:\.\d+)*[ .-]+)?(?:data|datasets?|materials and data)\b"),
        ("methods", r"\b(?:methods?|methodology|materials and methods|experimental setup)\b"),
        ("results", r"\bresults?\b"), ("discussion", r"\bdiscussion\b"),
        ("limitations", r"\blimitations?\b"), ("future_work", r"\bfuture work\b|future research"),
        ("conclusion", r"\bconclusions?\b|concluding remarks"),
        ("appendix", r"^(?:appendix|supplementary material|supporting information)\b"),
        ("acknowledgments", r"\backnowledg(?:e)?ments?\b"),
        ("author_contributions", r"\bauthor contributions?\b"),
    )
    for role, pattern in patterns:
        if re.search(pattern, title):
            return role, "normalized_heading_pattern"
    return "other", "normalized_heading_default"


def _phase_a_reference_boundary_conflict(
    text: str,
    section: Mapping[str, Any],
    reference_line_ranges: Sequence[tuple[int, int]],
) -> bool:
    """Return whether Phase A provenance conflicts with a structural reference reset.

    The condition is deliberately exact: after a structural reference reset, the
    candidate section must contain Markdown list items, and reference-labeled Phase A
    occurrences inside the section must reach both its first and last list-item lines.
    The signal requires review; it never extends reference scope.
    """

    section_start = int(section["start"])
    section_end = int(section["end"])
    section_start_line = text.count("\n", 0, section_start) + 1
    section_end_line = text.count("\n", 0, max(section_start, section_end - 1)) + 1
    list_lines = [
        text.count("\n", 0, section_start + start) + 1
        for start, _, line in _line_spans(text[section_start:section_end])
        if LIST_RE.match(line)
    ]
    if not list_lines:
        return False
    in_section = [
        (start, end)
        for start, end in reference_line_ranges
        if end >= section_start_line and start <= section_end_line
    ]
    return bool(
        in_section
        and min(start for start, _ in in_section) <= min(list_lines)
        and max(end for _, end in in_section) >= max(list_lines)
    )


def segment_sections(
    text: str,
    paper_id: str,
    reference_line_ranges: Sequence[tuple[int, int]] = (),
) -> list[dict[str, Any]]:
    """Partition a canonical document into sequential heading-delimited sections."""

    headings = recognized_headings(text)
    sections: list[dict[str, Any]] = []
    if not headings or headings[0]["start"] > 0:
        sections.append({"ordinal": 0, "start": 0, "end": headings[0]["start"] if headings else len(text), "level": 0, "raw": None, "normalized": "front matter", "path": []})
    stack: list[tuple[int, str]] = []
    for index, heading in enumerate(headings, start=1):
        section_id = f"pub:{paper_id}:sec:{index:04d}"
        while stack and stack[-1][0] >= heading["level"]:
            stack.pop()
        stack.append((heading["level"], section_id))
        sections.append({"ordinal": index, "start": heading["start"], "end": headings[index]["start"] if index < len(headings) else len(text), "level": heading["level"], "raw": heading["raw"], "normalized": normalize_section_title(heading["raw"]), "path": [item[1] for item in stack]})
    reference_level: int | None = None
    for section in sections:
        normalized = section["normalized"]
        reference_boundary_ambiguous = False
        if reference_level is not None:
            semantic_reset = bool(REFERENCE_RESET_RE.match(normalized))
            structural_reset = bool(section["level"] and section["level"] <= reference_level)
            if semantic_reset:
                reference_level = None
            elif structural_reset:
                reference_level = None
                if not REFERENCE_RE.match(normalized):
                    reference_boundary_ambiguous = _phase_a_reference_boundary_conflict(
                        text, section, reference_line_ranges
                    )
        role, rule = assign_section_role(None if section["raw"] is None else normalized)
        if REFERENCE_RE.match(normalized):
            reference_level = section["level"]
        if reference_level is not None:
            role, rule = "references", "reference_scope"
        section["role"], section["role_rule"] = role, rule
        section["reference_boundary_ambiguous"] = reference_boundary_ambiguous
        section["id"] = f"pub:{paper_id}:sec:{section['ordinal']:04d}"
        if section["ordinal"] == 0:
            section["path"] = [section["id"]]
    return sections


def _consume_blank_lines(lines: Sequence[tuple[int, int, str]], index: int) -> int:
    """Return the first line after blank separator lines."""

    while index < len(lines) and not lines[index][2].strip():
        index += 1
    return index


def _strip_visual_markup(value: str) -> str:
    """Remove only image markup for deterministic visual-only classification."""

    without_markdown = MARKDOWN_IMAGE_RE.sub("", value)
    return HTML_IMAGE_RE.sub("", without_markdown)


def is_visual_only_text(value: str) -> bool:
    """Return whether a block contains image markup and no independent text."""

    has_image = bool(MARKDOWN_IMAGE_RE.search(value) or HTML_IMAGE_RE.search(value))
    remainder = re.sub(r"<!--[\s\S]*?-->", "", _strip_visual_markup(value))
    return has_image and not remainder.strip()


def split_pipe_row(line: str) -> list[str]:
    """Split one Markdown pipe row while preserving escaped pipe characters."""

    stripped = line.strip()
    if stripped.startswith("|"):
        stripped = stripped[1:]
    if stripped.endswith("|") and not stripped.endswith(r"\|"):
        stripped = stripped[:-1]
    cells: list[str] = []
    current: list[str] = []
    escaped = False
    for character in stripped:
        if character == "|" and not escaped:
            cells.append("".join(current).strip())
            current = []
        else:
            current.append(character)
        if character == "\\" and not escaped:
            escaped = True
        else:
            escaped = False
    cells.append("".join(current).strip())
    return cells


def classify_pipe_table(value: str) -> tuple[str, list[int]]:
    """Classify table alignment and return unequivocally aligned data-row indexes."""

    lines = [line for line in value.splitlines() if line.strip()]
    if len(lines) < 2:
        return "broken", []
    header = split_pipe_row(lines[0])
    separator = split_pipe_row(lines[1])
    normalized_separator = [cell.replace(" ", "") for cell in separator]
    separator_valid = all(re.fullmatch(r":?-{3,}:?", cell) for cell in normalized_separator)
    converter_padding = (
        len(header) == len(separator)
        and len(header) > 1
        and not header[-1]
        and bool(re.fullmatch(r":?-{1,2}:?", normalized_separator[-1]))
        and all(re.fullmatch(r":?-{3,}:?", cell) for cell in normalized_separator[:-1])
    )
    rows = [split_pipe_row(line) for line in lines[2:]]
    if converter_padding and rows and all(len(row) == len(header) and not row[-1] for row in rows):
        return "partially_recoverable", list(range(2, len(lines)))
    if not separator_valid or len(header) != len(separator) or not header:
        return "broken", []
    safe_rows = [index for index, row in enumerate(rows, start=2) if len(row) == len(header)]
    if len(safe_rows) == len(lines) - 2:
        return "well_formed", safe_rows
    if safe_rows:
        return "partially_recoverable", safe_rows
    return "broken", []


def _looks_like_table_start(lines: Sequence[tuple[int, int, str]], index: int) -> bool:
    """Recognize valid and malformed pipe-table starts without repairing them."""

    if "|" not in lines[index][2] or index + 1 >= len(lines):
        return False
    next_line = lines[index + 1][2]
    return "|" in next_line and bool(re.search(r"-{3,}", next_line))


def parse_blocks(section_text: str, base_offset: int = 0) -> list[Span]:
    """Partition one section into exact contiguous Markdown block spans."""

    lines = _block_line_spans(section_text)
    blocks: list[Span] = []
    index = 0
    while index < len(lines):
        start_index = index
        line = lines[index][2]
        kind = "prose"
        table_quality: str | None = None
        needs_review = False
        review_reason: str | None = None
        supported_page_anchor = bool(PAGE_ANCHOR_PREFIX_RE.fullmatch(line))
        fence = FENCE_RE.match(line)
        if fence:
            kind = "code"
            marker = fence.group(1)
            closed = False
            index += 1
            while index < len(lines):
                closing = FENCE_RE.match(lines[index][2])
                index += 1
                if closing and closing.group(1)[0] == marker[0] and len(closing.group(1)) >= len(marker) and not closing.group(2).strip():
                    closed = True
                    break
            if not closed:
                needs_review, review_reason = True, "malformed_unclosed_fence"
        elif HEADING_RE.match(line):
            kind, index = "heading", index + 1
        elif line.lstrip().startswith(("$$", "\\[")):
            kind = "equation"
            closing_token = "$$" if line.lstrip().startswith("$$") else "\\]"
            closed = line.lstrip().count(closing_token) >= 2
            index += 1
            if not closed:
                while index < len(lines):
                    current = lines[index][2]
                    index += 1
                    if closing_token in current:
                        closed = True
                        break
            if not closed:
                needs_review, review_reason = True, "malformed_unclosed_equation"
        elif line.lstrip().startswith(">"):
            kind = "blockquote"
            index += 1
            while index < len(lines) and (lines[index][2].lstrip().startswith(">") or not lines[index][2].strip()):
                index += 1
        elif LIST_RE.match(line):
            kind = "list"
            index += 1
            while index < len(lines):
                current = lines[index][2]
                if not current.strip():
                    lookahead = _consume_blank_lines(lines, index)
                    if lookahead < len(lines) and LIST_RE.match(lines[lookahead][2]):
                        index = lookahead + 1
                        continue
                    break
                if LIST_RE.match(current) or current.startswith((" ", "\t")):
                    index += 1
                    continue
                break
        elif _looks_like_table_start(lines, index):
            kind = "table"
            index += 2
            while index < len(lines) and "|" in lines[index][2] and lines[index][2].strip():
                index += 1
            raw_table = section_text[lines[start_index][0]:(lines[index - 1][1] if index else len(section_text))]
            table_quality, _ = classify_pipe_table(raw_table)
        elif line.lstrip().startswith("<") and not supported_page_anchor:
            kind = "html"
            index += 1
            while index < len(lines) and lines[index][2].strip():
                index += 1
        elif CAPTION_RE.match(line):
            kind = "caption"
            index += 1
            while index < len(lines) and lines[index][2].strip():
                index += 1
        elif not line.strip() or supported_page_anchor:
            kind = "metadata"
            index += 1
            while index < len(lines) and (
                not lines[index][2].strip()
                or PAGE_ANCHOR_PREFIX_RE.fullmatch(lines[index][2])
            ):
                index += 1
        else:
            index += 1
            while index < len(lines) and lines[index][2].strip():
                if FENCE_RE.match(lines[index][2]) or LIST_RE.match(lines[index][2]) or lines[index][2].lstrip().startswith((">", "$$", "\\[")):
                    break
                index += 1
        index = _consume_blank_lines(lines, index)
        start = base_offset + lines[start_index][0]
        end = base_offset + (lines[index - 1][1] if index else lines[start_index][1])
        block_text = section_text[lines[start_index][0]:(end - base_offset)]
        contains_visual = bool(MARKDOWN_IMAGE_RE.search(block_text) or HTML_IMAGE_RE.search(block_text))
        visual_only = is_visual_only_text(block_text)
        if kind == "html":
            container = HTML_CONTAINER_RE.match(block_text)
            if container and not re.search(rf"</{re.escape(container.group(1))}\s*>", block_text, re.IGNORECASE):
                needs_review, review_reason = True, "malformed_unclosed_html_container"
        blocks.append(Span(start, end, kind, table_quality, False, needs_review, review_reason, visual_only, contains_visual))
    if blocks and blocks[-1].end != base_offset + len(section_text):
        block = blocks[-1]
        blocks[-1] = Span(block.start, base_offset + len(section_text), block.kind, block.table_quality, block.split_from_oversize, block.needs_review, block.review_reason, block.visual_only, block.contains_visual)
    return blocks


def _split_structured_block(block: Span, text: str) -> list[Span]:
    """Split an oversized table or list only at complete source-line items."""

    relative = text[block.start:block.end]
    lines = _line_spans(relative)
    boundaries = [0]
    if block.kind == "table":
        boundaries.extend(line[0] for line in lines[1:])
    else:
        boundaries.extend(line[0] for line in lines[1:] if LIST_RE.match(line[2]))
    boundaries.append(len(relative))
    parts: list[Span] = []
    part_start = boundaries[0]
    for boundary in boundaries[1:]:
        if boundary - part_start > PREFERRED_MAX and boundary != boundaries[1]:
            previous = boundaries[boundaries.index(boundary) - 1]
            parts.append(Span(block.start + part_start, block.start + previous, block.kind, block.table_quality, True, False, None, block.visual_only, block.contains_visual))
            part_start = previous
    if part_start < len(relative):
        parts.append(Span(block.start + part_start, block.end, block.kind, block.table_quality, True, False, None, block.visual_only, block.contains_visual))
    if any(part.end - part.start > ATOMIC_HARD_MAX for part in parts):
        return [Span(block.start, block.end, block.kind, block.table_quality, False, True, "oversize_atomic_block", block.visual_only, block.contains_visual)]
    return parts


def unitize_blocks(blocks: Sequence[Span], text: str) -> list[list[Span]]:
    """Assemble complete blocks into bounded, non-overlapping source units."""

    expanded: list[Span] = []
    for block in blocks:
        if block.end - block.start > ATOMIC_HARD_MAX:
            if block.kind in {"table", "list"}:
                expanded.extend(_split_structured_block(block, text))
            else:
                expanded.append(Span(block.start, block.end, block.kind, block.table_quality, False, True, "oversize_atomic_block", block.visual_only, block.contains_visual))
        else:
            expanded.append(block)
    units: list[list[Span]] = []
    current: list[Span] = []
    for block in expanded:
        if current and block.end - current[0].start > PREFERRED_MAX:
            units.append(current)
            current = []
        current.append(block)
        if block.end - block.start > PREFERRED_MAX or block.needs_review:
            units.append(current)
            current = []
    if current:
        units.append(current)
    return units


def _line_number(text: str, offset: int, end: bool = False) -> int:
    """Return a one-based inclusive source line for a half-open offset."""

    point = max(0, offset - 1) if end and offset else offset
    return text.count("\n", 0, point) + 1


def _eligibility(section_role: str, blocks: Sequence[Span]) -> tuple[str, list[str], bool]:
    """Classify unit eligibility without semantic screening or target inference."""

    visual_blocks = [block for block in blocks if block.visual_only]
    nonvisual_substantive = [block for block in blocks if block.kind not in {"heading", "metadata"} and not block.visual_only]
    if any(block.needs_review for block in blocks):
        return "needs_review", sorted({block.review_reason or "oversize_atomic_block" for block in blocks if block.needs_review}), False
    if section_role == "references":
        reasons = ["reference_section"]
        if visual_blocks and not nonvisual_substantive:
            reasons.append("visual_only_evidence")
        return "excluded", reasons, False
    if visual_blocks and not nonvisual_substantive:
        return "excluded", ["visual_only_evidence"], False
    if section_role in {"front_matter", "acknowledgments", "author_contributions"}:
        return "context_only", ["structural_or_metadata_only"], False
    substantive = {block.kind for block in nonvisual_substantive}
    if not substantive:
        return "context_only", ["structural_or_metadata_only"], False
    if substantive <= {"code"}:
        return "excluded", ["source_code_without_explanatory_prose"], False
    if substantive <= {"equation"}:
        return "excluded", ["equation_only_without_prose_support"], False
    if substantive <= {"table"}:
        table_qualities = {block.table_quality for block in nonvisual_substantive}
        if "broken" in table_qualities:
            return "excluded", ["unrecoverable_table_structure"], False
        if "partially_recoverable" in table_qualities:
            return "needs_review", ["partially_recoverable_table_requires_review"], False
    return "eligible", [], True


def _block_metadata(blocks: Sequence[Span], has_explanatory_prose: bool) -> list[dict[str, Any]]:
    """Create block-level evidence eligibility without changing canonical spans."""

    result: list[dict[str, Any]] = []
    for block in blocks:
        reasons: list[str] = []
        evidence_eligible = block.kind not in {"heading", "metadata", "code"}
        if block.visual_only:
            evidence_eligible = False
            reasons.append("visual_only_evidence")
        if block.kind == "equation" and not has_explanatory_prose:
            evidence_eligible = False
            reasons.append("equation_only_without_prose_support")
        if block.kind == "table" and block.table_quality != "well_formed":
            evidence_eligible = False
            reasons.append("unrecoverable_table_structure" if block.table_quality == "broken" else "partially_recoverable_table_requires_review")
        if block.needs_review:
            evidence_eligible = False
            reasons.append(block.review_reason or "oversize_atomic_block")
        result.append({
            "blockType": block.kind, "startOffsetInDocument": block.start,
            "endOffsetInDocument": block.end, "splitFromOversize": block.split_from_oversize,
            "tableQuality": block.table_quality, "blockEligibility": "eligible" if evidence_eligible else ("needs_review" if block.needs_review or block.table_quality == "partially_recoverable" else "excluded"),
            "blockExclusionReasons": sorted(set(reasons)), "evidenceEligible": evidence_eligible,
            "visualOnly": block.visual_only, "reviewReason": block.review_reason,
            "containsVisual": block.contains_visual, "imageMarkupEvidenceEligible": False if block.contains_visual else None,
        })
    return result


def build_document_units(record: Mapping[str, Any], raw: bytes, phase_schema: str, phase_version: str) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Build and validate every canonical unit for one Phase A publication."""

    paper_id = str(record["local_paper_id"])
    source_file = str(record["source_files"]["markdown_path"])
    text = normalize_canonical_text(raw)
    raw_hash, canonical_hash = sha256_bytes(raw), sha256_bytes(text.encode("utf-8"))
    reference_line_ranges = sorted({
        (int(location["line_start"]), int(location["line_end"]))
        for reference in record.get("content", {}).get("reference_dois", [])
        for occurrence in reference.get("occurrences", [])
        for location in [occurrence.get("source_location", {})]
        if REFERENCE_RE.match(normalize_section_title(str(location.get("section", ""))))
        and location.get("line_start") is not None
        and location.get("line_end") is not None
    })
    sections = segment_sections(text, paper_id, reference_line_ranges)
    units: list[dict[str, Any]] = []
    for section in sections:
        section_text = text[section["start"]:section["end"]]
        blocks = parse_blocks(section_text, section["start"])
        for chunk_number, unit_blocks in enumerate(unitize_blocks(blocks, text), start=1):
            start, end = unit_blocks[0].start, unit_blocks[-1].end
            unit_text = text[start:end]
            source_unit_id = f"{section['id']}:unit:{chunk_number:04d}"
            eligibility, reasons, request_eligible = _eligibility(section["role"], unit_blocks)
            if section["reference_boundary_ambiguous"]:
                eligibility = "needs_review"
                reasons = ["ambiguous_reference_section_boundary"]
                request_eligible = False
            content_types = sorted({block.kind for block in unit_blocks})
            table_qualities = {block.table_quality for block in unit_blocks if block.table_quality}
            table_quality = max(table_qualities, key=TABLE_QUALITY_ORDER.__getitem__) if table_qualities else None
            has_explanatory_prose = any(block.kind == "prose" and not block.visual_only for block in unit_blocks)
            block_metadata = _block_metadata(unit_blocks, has_explanatory_prose)
            review_reasons = (
                ["ambiguous_reference_section_boundary"]
                if section["reference_boundary_ambiguous"]
                else sorted({block.review_reason for block in unit_blocks if block.review_reason})
            )
            projection = {"contractVersion": CONTRACT_VERSION, "paperID": paper_id, "sourceFile": source_file, "canonicalTextSha256": canonical_hash, "sourceUnitID": source_unit_id, "sectionID": section["id"], "chunkNumber": chunk_number, "startOffsetInDocument": start, "endOffsetInDocument": end, "text": unit_text}
            unit = {
                "contractVersion": CONTRACT_VERSION, "paperID": paper_id,
                "canonicalArtifactID": record["canonical_artifact_id"], "recordType": record["record_type"],
                "phaseASchemaVersion": phase_schema, "phaseAVersion": phase_version,
                "sourceFile": source_file, "rawFileSha256": raw_hash, "canonicalTextSha256": canonical_hash,
                "sourceUnitID": source_unit_id, "sectionID": section["id"], "sectionOrdinal": section["ordinal"],
                "sectionLevel": section["level"], "sectionTitleRaw": section["raw"], "sectionTitleNormalized": section["normalized"],
                "sectionPath": section["path"], "sectionRole": section["role"], "sectionRoleRule": section["role_rule"],
                "chunkNumber": chunk_number, "contentTypes": content_types, "eligibility": eligibility,
                "exclusionReasons": reasons, "text": unit_text,
                "sectionStartOffsetInDocument": section["start"], "sectionEndOffsetInDocument": section["end"],
                "startOffsetInDocument": start, "endOffsetInDocument": end,
                "startOffsetInSection": start - section["start"], "endOffsetInSection": end - section["start"],
                "startLine": _line_number(text, start), "endLine": _line_number(text, end, True),
                "textHash": sha256_bytes(unit_text.encode("utf-8")), "inputHash": sha256_bytes(canonical_json(projection)),
                "markerBlockRefs": [], "pageRefs": [], "deterministicNodeRefs": [], "deterministicEdgeRefs": [],
                "deferredRecordRefs": [], "eligibleCategories": [], "eligibleOperationalTargetIDs": [],
                "adjacentUnitRefs": {"previous": None, "next": None},
                "characterCount": len(unit_text), "atomicBlockCount": len(unit_blocks),
                "blockMetadata": block_metadata,
                "tableQuality": table_quality,
                "requestEligible": request_eligible, "validationResults": {"valid": True, "errorCodes": []},
                "reviewRequired": eligibility == "needs_review", "reviewReasons": review_reasons,
            }
            units.append(unit)
    for index, unit in enumerate(units):
        same_section = [candidate for candidate in units if candidate["sectionID"] == unit["sectionID"]]
        local_index = same_section.index(unit)
        unit["adjacentUnitRefs"] = {"previous": same_section[local_index - 1]["sourceUnitID"] if local_index else None, "next": same_section[local_index + 1]["sourceUnitID"] if local_index + 1 < len(same_section) else None}
    validate_document_units(text, sections, units, raw=raw, expected_source_file=source_file)
    return units, {"rawFileSha256": raw_hash, "canonicalTextSha256": canonical_hash, "sectionCount": len(sections)}


def collect_validation_errors(
    text: str,
    sections: Sequence[Mapping[str, Any]],
    units: Sequence[Mapping[str, Any]],
    *,
    raw: bytes | None = None,
    expected_source_file: str | None = None,
    known_operational_targets: set[str] | None = None,
    out_of_scope_targets: set[str] | None = None,
    abstract_targets: set[str] | None = None,
) -> list[str]:
    """Recompute structural, hash, routing, quality, and request invariants."""

    found: set[str] = set()
    ordered_sections = sorted(sections, key=lambda item: int(item["start"]))
    previous_end = 0
    for section in ordered_sections:
        start, end = int(section["start"]), int(section["end"])
        if start > previous_end:
            found.add("SECTION_PARTITION_GAP")
        if start < previous_end:
            found.add("SECTION_PARTITION_OVERLAP")
        previous_end = max(previous_end, end)
    if previous_end < len(text):
        found.add("SECTION_PARTITION_GAP")
    if any(ord(character) < 32 and character not in "\t\n" for character in text):
        found.add("FORBIDDEN_CONTROL_CHARACTER_UNSANITIZED")
    canonical_hash = sha256_bytes(text.encode("utf-8"))
    raw_hash = sha256_bytes(raw) if raw is not None else None
    if len({str(unit.get("sourceUnitID")) for unit in units}) != len(units):
        found.add("OFFSET_MISMATCH")
    valid_categories = {f"B-P{index:02d}" for index in range(1, 14)}
    known_targets = known_operational_targets or set()
    out_of_scope = out_of_scope_targets or set()
    abstract = abstract_targets or set()
    for section in ordered_sections:
        section_units = sorted(
            (unit for unit in units if unit.get("sectionID") == section["id"]),
            key=lambda item: int(item.get("startOffsetInDocument", -1)),
        )
        prior = int(section["start"])
        for unit in section_units:
            start = int(unit.get("startOffsetInDocument", -1))
            end = int(unit.get("endOffsetInDocument", -1))
            if start > prior:
                found.add("UNIT_PARTITION_GAP")
            if start < prior:
                found.add("UNIT_PARTITION_OVERLAP")
            prior = max(prior, end)
        if prior < int(section["end"]):
            found.add("UNIT_PARTITION_GAP")
    for unit in units:
        start = int(unit.get("startOffsetInDocument", -1))
        end = int(unit.get("endOffsetInDocument", -1))
        section_start = int(unit.get("sectionStartOffsetInDocument", -1))
        section_end = int(unit.get("sectionEndOffsetInDocument", -1))
        if start < section_start or end > section_end or start > end:
            found.add("UNIT_OUTSIDE_SECTION")
        if unit.get("text") != text[start:end]:
            found.add("UNIT_TEXT_MISMATCH")
        expected_section_id = f"pub:{unit.get('paperID')}:sec:{int(unit.get('sectionOrdinal', -1)):04d}"
        expected_unit_id = f"{expected_section_id}:unit:{int(unit.get('chunkNumber', -1)):04d}"
        if (
            unit.get("sectionID") != expected_section_id
            or unit.get("sourceUnitID") != expected_unit_id
            or unit.get("startOffsetInSection") != start - section_start
            or unit.get("endOffsetInSection") != end - section_start
        ):
            found.add("OFFSET_MISMATCH")
        if unit.get("startLine") != _line_number(text, start) or unit.get("endLine") != _line_number(text, end, True):
            found.add("LINE_RANGE_MISMATCH")
        if unit.get("textHash") != sha256_bytes(str(unit.get("text", "")).encode("utf-8")):
            found.add("TEXT_HASH_MISMATCH")
        projection = {key: unit.get(key) for key in (
            "contractVersion", "paperID", "sourceFile", "canonicalTextSha256",
            "sourceUnitID", "sectionID", "chunkNumber", "startOffsetInDocument",
            "endOffsetInDocument", "text",
        )}
        if unit.get("inputHash") != sha256_bytes(canonical_json(projection)):
            found.add("INPUT_HASH_MISMATCH")
        if expected_source_file is not None and unit.get("sourceFile") != expected_source_file:
            found.add("SOURCE_PATH_MISMATCH")
        if raw_hash is not None and unit.get("rawFileSha256") != raw_hash:
            found.add("RAW_FILE_HASH_MISMATCH")
        if unit.get("canonicalTextSha256") != canonical_hash:
            found.add("CANONICAL_TEXT_HASH_MISMATCH")
        if unit.get("sectionRole") not in SECTION_ROLES:
            found.add("UNKNOWN_SECTION_ROLE")
        if not set(unit.get("contentTypes", [])) <= CONTENT_TYPES:
            found.add("UNKNOWN_CONTENT_TYPE")
        if unit.get("eligibility") not in ELIGIBILITIES or (unit.get("eligibility") in {"excluded", "needs_review"} and unit.get("requestEligible")):
            found.add("UNKNOWN_ELIGIBILITY")
        categories = set(unit.get("eligibleCategories", []))
        if not categories <= valid_categories:
            found.add("UNKNOWN_ROUTING_CATEGORY")
        targets = set(unit.get("eligibleOperationalTargetIDs", []))
        if known_operational_targets is not None and not targets <= known_targets:
            found.add("UNKNOWN_OPERATIONAL_TARGET")
        if targets & out_of_scope:
            found.add("OUT_OF_SCOPE_TARGET_ROUTED")
        if targets & abstract:
            found.add("ABSTRACT_TARGET_ROUTED")
        if unit.get("sectionRole") == "references" and unit.get("sectionRoleRule") not in {"reference_scope", "normalized_heading_pattern"}:
            found.add("REFERENCE_SCOPE_AMBIGUOUS")
        for block in unit.get("blockMetadata", []):
            length = int(block.get("endOffsetInDocument", 0)) - int(block.get("startOffsetInDocument", 0))
            if length > ATOMIC_HARD_MAX and not block.get("splitFromOversize") and not unit.get("reviewRequired"):
                found.add("OVERSIZE_ATOMIC_BLOCK")
            quality = block.get("tableQuality")
            if block.get("blockType") == "table" and quality not in TABLE_QUALITY_ORDER:
                found.add("BROKEN_TABLE_STRUCTURE")
            if quality == "broken" and (block.get("evidenceEligible") or unit.get("requestEligible") and len(unit.get("contentTypes", [])) == 1):
                found.add("BROKEN_TABLE_STRUCTURE")
        qualities = [block.get("tableQuality") for block in unit.get("blockMetadata", []) if block.get("tableQuality")]
        expected_quality = max(qualities, key=TABLE_QUALITY_ORDER.__getitem__) if qualities and set(qualities) <= TABLE_QUALITY_ORDER.keys() else None
        if qualities and unit.get("tableQuality") != expected_quality:
            found.add("BROKEN_TABLE_STRUCTURE")
    return [code for code in STABLE_ERROR_CODES if code in found]


def validate_document_units(
    text: str,
    sections: Sequence[Mapping[str, Any]],
    units: Sequence[Mapping[str, Any]],
    **kwargs: Any,
) -> None:
    """Raise a stable-code failure when recomputed validation finds any error."""

    missing = sorted({field for unit in units for field in REQUIRED_SOURCE_UNIT_FIELDS if field not in unit})
    if missing:
        raise SourceUnitError(f"required source-unit fields missing: {', '.join(missing)}")
    errors = collect_validation_errors(text, sections, units, **kwargs)
    if errors:
        raise SourceUnitError(", ".join(errors))


def natural_paper_key(value: str) -> tuple[int, str]:
    """Sort numeric paper IDs naturally, with suffix records after their base."""

    match = re.match(r"^(\d+)(.*)$", value)
    return (int(match.group(1)), match.group(2)) if match else (10**12, value)


def load_phase_a_records(corpus_path: Path, artifact_ids: Sequence[str]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Load exactly one distinct Phase A record for every requested artifact ID."""

    corpus = json.loads(corpus_path.read_text(encoding="utf-8"))
    if len(artifact_ids) != 12 or len(set(artifact_ids)) != 12:
        raise SourceUnitError("population must contain exactly twelve distinct artifact IDs")
    grouped: dict[str, list[dict[str, Any]]] = {}
    for record in corpus.get("publications", []):
        grouped.setdefault(str(record.get("local_paper_id")), []).append(record)
    missing = [artifact_id for artifact_id in artifact_ids if len(grouped.get(artifact_id, [])) != 1]
    if missing:
        raise SourceUnitError(f"Phase A records must resolve exactly once: {missing}")
    records = [grouped[artifact_id][0] for artifact_id in artifact_ids]
    return corpus, records


def validate_source_file(path: Path, recorded_path: str, expected_path: str) -> None:
    """Validate exact Phase A path identity and canonical source availability."""

    if recorded_path != expected_path:
        raise SourceUnitError("SOURCE_PATH_MISMATCH")
    if not path.is_file():
        raise SourceUnitError(f"SOURCE_FILE_NOT_FOUND: {recorded_path}")


def _sidecar_hash(root: Path, path_value: str | None) -> str | None:
    """Hash one available retained Marker sidecar without inventing provenance."""

    if not path_value:
        return None
    path = root / path_value
    return sha256_bytes(path.read_bytes()) if path.is_file() else None


def _verify_frozen_authorities(project_root: Path, phase_b_path: Path) -> dict[str, Any]:
    """Verify every direct materialization authority and return byte-derived provenance."""

    authorities = (
        (project_root / "docs/publication_source_unit_contract.md", CONTRACT_HASH),
        (project_root / "src/extraction/llm/publications/publication_target_inventory.yaml", TARGET_INVENTORY_HASH),
        (project_root / "src/ontology/ciroh_ontology.owl", ONTOLOGY_OWL_HASH),
        (phase_b_path, PHASE_B_HASH),
    )
    verified: dict[str, str] = {}
    phase_b_version: str | None = None
    for path, expected_hash in authorities:
        display_path = str(path.relative_to(project_root)) if path.is_relative_to(project_root) else str(path)
        if not path.is_file():
            raise SourceUnitError(f"BLOCKED_BY_FROZEN_AUTHORITY_DRIFT: path={display_path} reason=missing")
        if path == phase_b_path:
            phase_b_version = json.loads(path.read_text(encoding="utf-8")).get("phase_b_version")
            if phase_b_version != PHASE_B_VERSION:
                raise SourceUnitError(f"BLOCKED_BY_FROZEN_AUTHORITY_DRIFT: path={display_path} reason=version_mismatch")
        actual_hash = sha256_bytes(path.read_bytes())
        if actual_hash != expected_hash:
            raise SourceUnitError(f"BLOCKED_BY_FROZEN_AUTHORITY_DRIFT: path={display_path} reason=hash_mismatch")
        verified[display_path] = actual_hash
    return {
        "sourceUnitContractHash": verified["docs/publication_source_unit_contract.md"],
        "targetInventoryHash": verified["src/extraction/llm/publications/publication_target_inventory.yaml"],
        "ontologyOwlSha256": verified["src/ontology/ciroh_ontology.owl"],
        "phaseBArtifactHash": verified[str(phase_b_path.relative_to(project_root))],
        "phaseBVersion": phase_b_version,
    }


def build_inventory(
    project_root: Path,
    corpus_path: Path,
    artifact_ids: Sequence[str],
    generation_timestamp: str,
    phase_b_path: Path | None = None,
    *,
    verify_frozen_authorities: bool = True,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Build the complete inventory and its manifest entirely in memory."""

    resolved_phase_b_path = phase_b_path or project_root / "data/interim/papers/publication_nodes_edges.json"
    authority_provenance = _verify_frozen_authorities(project_root, resolved_phase_b_path) if verify_frozen_authorities else {
        "sourceUnitContractHash": None, "targetInventoryHash": None,
        "ontologyOwlSha256": None, "phaseBArtifactHash": None, "phaseBVersion": None,
    }
    corpus, records = load_phase_a_records(corpus_path, artifact_ids)
    all_units: list[dict[str, Any]] = []
    artifacts: list[dict[str, Any]] = []
    canonical_hashes: dict[str, str] = {}
    for record in records:
        source_file = str(record["source_files"].get("markdown_path") or "")
        path = project_root / source_file
        validate_source_file(path, source_file, str(record["source_files"].get("markdown_path") or ""))
        units, document = build_document_units(record, path.read_bytes(), corpus["schema_version"], corpus["phase_a_version"])
        all_units.extend(units)
        eligibility_counts = Counter(unit["eligibility"] for unit in units)
        canonical_hashes[str(record["local_paper_id"])] = document["canonicalTextSha256"]
        sidecars = record["source_files"]
        phase_a_warnings = list(record.get("reconciliation", {}).get("warnings", []))
        control_warning = any(item.get("category") == "unexpected_control_characters" for item in phase_a_warnings)
        artifacts.append({
            "paperID": str(record["local_paper_id"]), "canonicalArtifactID": record["canonical_artifact_id"],
            "recordType": record["record_type"], "sourceFile": source_file,
            "rawFileSha256": document["rawFileSha256"], "canonicalTextSha256": document["canonicalTextSha256"],
            "markerVersion": None, "markerVersionStatus": "unavailable_with_justification",
            "markerVersionJustification": "Marker version is not retained in the reviewed Phase A corpus or sidecar metadata.",
            "chunksSha256": _sidecar_hash(project_root, sidecars.get("chunks_path")),
            "chunksMetadataSha256": _sidecar_hash(project_root, sidecars.get("chunks_meta_path")),
            "markdownMetadataSha256": _sidecar_hash(project_root, sidecars.get("markdown_meta_path")),
            "sourceUnitCount": len(units), "sectionCount": document["sectionCount"],
            "eligibilityCounts": dict(sorted(eligibility_counts.items())),
            "conversionStatusSummary": "canonical_markdown_sanitized_forbidden_controls" if control_warning else "canonical_markdown_available",
            "conversionWarnings": phase_a_warnings, "warningCount": len(phase_a_warnings),
            "needsReviewCount": eligibility_counts["needs_review"], "validationResults": {"valid": True, "errorCodes": []},
            "imageContainingUnitCount": sum(any(block["visualOnly"] or "![" in unit["text"] or "<img" in unit["text"].casefold() for block in unit["blockMetadata"]) for unit in units),
            "visualOnlyUnitCount": sum(unit["exclusionReasons"] == ["visual_only_evidence"] or "visual_only_evidence" in unit["exclusionReasons"] for unit in units),
            "tableContainingUnitCount": sum("table" in unit["contentTypes"] for unit in units),
            "equationContainingUnitCount": sum("equation" in unit["contentTypes"] for unit in units),
        })
    all_units.sort(key=lambda unit: (natural_paper_key(unit["paperID"]), unit["sectionOrdinal"], unit["chunkNumber"]))
    inventory_bytes = serialize_inventory(all_units)
    config = {"artifactIDs": list(artifact_ids), "preferredUnitMaxCharacters": PREFERRED_MAX, "atomicBlockHardMaxCharacters": ATOMIC_HARD_MAX, "overlapCharacters": 0, "crossSectionUnitsAllowed": False, "ordinaryParagraphSplittingAllowed": False}
    phase_b_hash = authority_provenance["phaseBArtifactHash"]
    phase_b_version = authority_provenance["phaseBVersion"]
    image_units = [unit for unit in all_units if any(block["containsVisual"] for block in unit["blockMetadata"])]
    equation_units = [unit for unit in all_units if "equation" in unit["contentTypes"]]
    table_units = [unit for unit in all_units if "table" in unit["contentTypes"]]
    eligibility_counts = Counter(unit["eligibility"] for unit in all_units)
    content_audit = {
        "imageContainingUnitCount": len(image_units),
        "pureVisualOnlyUnitCount": sum("visual_only_evidence" in unit["exclusionReasons"] for unit in image_units),
        "mixedTextualVisualUnitCount": sum("visual_only_evidence" not in unit["exclusionReasons"] for unit in image_units),
        "tableContainingUnitCount": len(table_units),
        "tableQualityCounts": dict(sorted(Counter(unit["tableQuality"] for unit in table_units).items())),
        "equationContainingUnitCount": len(equation_units),
        "equationOnlyUnitCount": sum("equation_only_without_prose_support" in unit["exclusionReasons"] for unit in equation_units),
        "equationWithSameUnitProseSupportCount": sum(any(block["blockType"] == "equation" and block["evidenceEligible"] for block in unit["blockMetadata"]) for unit in equation_units),
        "equationWithNonEvidenceBlockCount": sum(any(block["blockType"] == "equation" and not block["evidenceEligible"] for block in unit["blockMetadata"]) for unit in equation_units),
        "malformedOrReviewUnitCount": sum(unit["reviewRequired"] for unit in all_units),
    }
    manifest = {
        "builderVersion": BUILDER_VERSION, "generatorVersion": BUILDER_VERSION,
        "contractVersion": CONTRACT_VERSION, "sourceUnitContractVersion": CONTRACT_VERSION,
        "sourceUnitContractHash": authority_provenance["sourceUnitContractHash"], "artifactCount": len(artifacts),
        "sectionCount": sum(artifact["sectionCount"] for artifact in artifacts),
        "sourceUnitCount": len(all_units), "eligibilityCounts": dict(sorted(eligibility_counts.items())),
        "needsReviewCount": eligibility_counts["needs_review"], "contentAuditSummary": content_audit,
        "canonicalDocumentHashes": canonical_hashes, "sourceUnitInventoryHash": sha256_bytes(inventory_bytes),
        "generatedAt": generation_timestamp, "generationTimestamp": generation_timestamp,
        "generationEnvironment": {"implementation": "python", "networkAccess": False, "llmAccess": False},
        "validationResults": {"valid": True, "artifactCount": len(artifacts), "sourceUnitCount": len(all_units), "errorCodes": []},
        "phaseASchemaVersion": corpus["schema_version"], "phaseAVersion": corpus["phase_a_version"],
        "phaseBVersion": phase_b_version, "phaseBArtifactHash": phase_b_hash,
        "targetInventoryVersion": TARGET_INVENTORY_VERSION, "targetInventoryHash": authority_provenance["targetInventoryHash"],
        "ontologyVersion": ONTOLOGY_VERSION, "ontologyOwlSha256": authority_provenance["ontologyOwlSha256"],
        "canonicalCorpusSha256": sha256_bytes(corpus_path.read_bytes()),
        "configurationSha256": sha256_bytes(canonical_json(config)),
        "sourceUnitBuilderConfigurationHash": sha256_bytes(canonical_json(config)),
        "sourceUnitBuilderConfiguration": config, "artifactRecords": artifacts,
    }
    return all_units, manifest


def serialize_inventory(units: Iterable[Mapping[str, Any]]) -> bytes:
    """Serialize deterministic sorted-key LF-terminated JSONL bytes."""

    return b"".join(canonical_json(unit) + b"\n" for unit in units)


def serialize_manifest(manifest: Mapping[str, Any]) -> bytes:
    """Serialize a deterministic, reviewable manifest with one final LF."""

    return (json.dumps(manifest, indent=2, ensure_ascii=False, sort_keys=True) + "\n").encode("utf-8")


def write_outputs_atomically(outputs: Sequence[tuple[Path, bytes]]) -> None:
    """Prepare every output and restore prior bytes if any replacement fails."""

    temporary_paths: list[tuple[Path, Path]] = []
    backup_paths: list[tuple[Path, Path]] = []
    replaced: list[Path] = []
    try:
        for destination, payload in outputs:
            destination.parent.mkdir(parents=True, exist_ok=True)
            with tempfile.NamedTemporaryFile(mode="wb", dir=destination.parent, prefix=f".{destination.name}.", delete=False) as handle:
                handle.write(payload)
                handle.flush()
                os.fsync(handle.fileno())
                temporary_paths.append((Path(handle.name), destination))
            if destination.exists():
                with tempfile.NamedTemporaryFile(mode="wb", dir=destination.parent, prefix=f".{destination.name}.backup.", delete=False) as backup:
                    backup.write(destination.read_bytes())
                    backup.flush()
                    os.fsync(backup.fileno())
                    backup_paths.append((Path(backup.name), destination))
        for temporary, destination in temporary_paths:
            os.replace(temporary, destination)
            replaced.append(destination)
    except OSError:
        backups = {destination: backup for backup, destination in backup_paths}
        for destination in reversed(replaced):
            backup = backups.get(destination)
            if backup and backup.exists():
                os.replace(backup, destination)
            elif destination.exists():
                destination.unlink()
        raise
    finally:
        for temporary, _ in temporary_paths:
            if temporary.exists():
                temporary.unlink()
        for backup, _ in backup_paths:
            if backup.exists():
                backup.unlink()
