"""In-memory Hub MDX reader under frozen Step 11 v0.3 §§2 and 5.1.

Only supplied content_mdx is authoritative. This bounded visibility scanner does
not render MDX or interpret code. Units are source context, never KG assertions.
"""

from __future__ import annotations

from copy import deepcopy
import hashlib
import json
import re
from typing import Any, Mapping


CONTRACT_ID = "study2-step11-semantic-contracts/v0.3"
PROVENANCE = ("page_key", "canonical_url", "corpus_path", "source_path", "source_group",
              "content_sha256", "file_sha256", "generated_from_js")
HEADING = re.compile(r"^ {0,3}(#{1,6})[ \t]+(.+?)[ \t]*#*[ \t]*$")
FENCE = re.compile(r"^ {0,3}(`{3,}|~{3,})([^\r\n]*)")
STATIC_TAGS = frozenset({"p", "strong", "em", "b", "i", "ul", "ol", "li",
                         "table", "thead", "tbody", "tr", "td", "th", "blockquote"})


def _sha(text: str) -> str:
    """Hash the exact UTF-8 representation without normalization."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _dynamic_end(lines: list[str], index: int) -> int:
    """Skip a lexical JS block, including blank lines inside brackets/strings.

    This identifies an opaque boundary only; no expressions are interpreted.
    Unbalanced/uncertain syntax conservatively consumes the remaining input.
    """
    depth = 0
    quote: str | None = None
    escaped = False
    block_comment = False
    while index < len(lines):
        line = lines[index]
        cursor = 0
        while cursor < len(line):
            char = line[cursor]
            if block_comment:
                if line.startswith("*/", cursor):
                    block_comment = False
                    cursor += 2
                    continue
            elif quote:
                if escaped:
                    escaped = False
                elif char == "\\":
                    escaped = True
                elif char == quote:
                    quote = None
            elif line.startswith("//", cursor):
                break
            elif line.startswith("/*", cursor):
                block_comment = True
                cursor += 2
                continue
            elif char in "\"'`":
                quote = char
            elif char in "{([":
                depth += 1
            elif char in "})]":
                depth -= 1
            cursor += 1
        index += 1
        if depth == 0 and quote is None and not block_comment:
            return index
    return index


def read_page_source_units(
    page: Mapping[str, Any], *, accepted_section_mapping: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Read one frozen page with optional caller-trusted Section bindings.

    Mapping shape: page_key, canonical_url, content_sha256, and sections (a list
    of heading_ordinal, source_line, raw_text, section_id records). Caller supplies
    accepted IDs; this reader checks snapshot/heading correspondence and never
    creates a Section. Missing mappings leave sectionID null.

    Coordinates are half-open Unicode offsets in original content_mdx; lines are
    one-based, with endLine referring to the last included character. Successful
    reads verify only content_sha256, not original acquisition/file_sha256.
    """
    context = {key: deepcopy(page[key]) for key in PROVENANCE if key in page}
    context.update({"artifactFamily": "ciroh_hub", "contractID": CONTRACT_ID})
    result: dict[str, Any] = {"status": "source_read_success", "authority": None,
                              "sourceUnits": [], "diagnostics": [], "reviewRequired": False}

    def diagnostic(reason: str, *, failed: bool = False, **location: Any) -> None:
        """Separate technical failure from unresolved visibility/binding."""
        status = "failed_source_or_evidence_binding" if failed else "needs_review"
        result["diagnostics"].append({**deepcopy(context), **location, "status": status, "reason": reason})
        if failed:
            result["status"] = status
        else:
            result["reviewRequired"] = True

    for key in ("page_key", "canonical_url", "corpus_path", "source_path", "source_group"):
        if not isinstance(page.get(key), str) or not page[key].strip():
            diagnostic("required_source_field_missing_or_malformed", failed=True, field=key)
    text, expected = page.get("content_mdx"), page.get("content_sha256")
    if not isinstance(text, str):
        diagnostic("required_source_field_missing_or_malformed", failed=True, field="content_mdx")
    if not isinstance(expected, str) or re.fullmatch(r"[0-9a-f]{64}", expected) is None:
        diagnostic("required_source_field_missing_or_malformed", failed=True, field="content_sha256")
    if "file_sha256" in page and (not isinstance(page["file_sha256"], str)
                                  or re.fullmatch(r"[0-9a-f]{64}", page["file_sha256"]) is None):
        diagnostic("source_provenance_malformed", failed=True, field="file_sha256")
    if "generated_from_js" in page and type(page["generated_from_js"]) is not bool:
        diagnostic("source_provenance_malformed", failed=True, field="generated_from_js")
    if result["status"] != "source_read_success":
        return result
    try:
        actual = _sha(text)
    except UnicodeEncodeError:
        diagnostic("source_text_malformed", failed=True, field="content_mdx")
        return result
    if actual != expected:
        diagnostic("source_content_integrity_failure", failed=True, computedSha256=actual)
        return result
    context["authorityTextSha256"] = actual
    result["authority"] = {**deepcopy(context), "text": text,
                           "integrityStatus": "matched_supplied_content_sha256",
                           "fileIntegrityStatus": "not_checked"}
    lines = text.splitlines(keepends=True)
    offsets = [0]
    for line in lines:
        offsets.append(offsets[-1] + len(line))
    headings: dict[int, Mapping[str, Any]] = {}
    supplied = page.get("headings", [])
    if not isinstance(supplied, list):
        diagnostic("heading_metadata_malformed")
        supplied = []
    ordinals = [h.get("ordinal") for h in supplied if isinstance(h, Mapping)]
    heading_lines = [h.get("source_line") for h in supplied if isinstance(h, Mapping)]
    for h in supplied:
        if not isinstance(h, Mapping):
            diagnostic("heading_metadata_malformed")
            continue
        number, ordinal = h.get("source_line"), h.get("ordinal")
        valid = (type(number) is int and 1 <= number <= len(lines) and type(ordinal) is int
                 and ordinal > 0 and ordinals.count(ordinal) == 1 and heading_lines.count(number) == 1)
        match = HEADING.match(lines[number - 1].rstrip("\r\n")) if valid else None
        if (not match or match.group(2).strip() != h.get("raw_text")
                or len(match.group(1)) != h.get("level") or number in headings):
            diagnostic("heading_mapping_unverified", sourceLine=number)
            continue
        headings[number] = h
    sections: dict[int, str] = {}
    if accepted_section_mapping is not None:
        mapping = accepted_section_mapping
        if (not isinstance(mapping, Mapping)
                or any(mapping.get(k) != page[k] for k in ("page_key", "canonical_url", "content_sha256"))
                or not isinstance(mapping.get("sections"), list)):
            diagnostic("section_mapping_snapshot_mismatch")
        else:
            rows = mapping["sections"]
            ids = [r.get("section_id") for r in rows if isinstance(r, Mapping)]
            mapped_ordinals = [r.get("heading_ordinal") for r in rows if isinstance(r, Mapping)]
            for row in rows:
                if not isinstance(row, Mapping):
                    diagnostic("section_mapping_unverified")
                    continue
                ordinal, number, section = row.get("heading_ordinal"), row.get("source_line"), row.get("section_id")
                h = headings.get(number) if type(number) is int else None
                if (not h or type(ordinal) is not int or h["ordinal"] != ordinal or row.get("raw_text") != h["raw_text"]
                        or not isinstance(section, str) or not section
                        or ids.count(section) != 1 or mapped_ordinals.count(ordinal) != 1):
                    diagnostic("section_mapping_unverified", sourceLine=number)
                    continue
                sections[ordinal] = section

    heading: Mapping[str, Any] | None = None
    heading_text: str | None = None

    def emit(start: int, end: int, first: int, last: int, kind: str) -> None:
        """Emit a literal bounded source span with no graph/type assertion."""
        ordinal = heading["ordinal"] if heading else None
        identity = json.dumps([page["page_key"], actual, start, end, kind], separators=(",", ":"))
        result["sourceUnits"].append({
            **deepcopy(context), "sourceUnitID": "hub:unit:" + _sha(identity),
            "text": text[start:end], "startOffsetInAuthority": start, "endOffsetInAuthority": end,
            "startLine": first, "endLine": last, "headingOrdinal": ordinal,
            "headingContext": heading_text, "sectionID": sections.get(ordinal),
            "contentKind": kind, "eligibility": "possible_example_context" if kind == "fenced_snippet" else "static_visible_context",
        })

    index = 0
    wrappers: list[tuple[str, int]] = []
    while index < len(lines):
        line, number = lines[index], index + 1
        stripped = line.strip()
        start, end = offsets[index], offsets[index + 1]
        index += 1
        if not stripped:
            continue
        fence = FENCE.match(line)
        if fence:
            token = fence.group(1)
            closing = index
            while closing < len(lines):
                match = FENCE.match(lines[closing])
                if match and match.group(1)[0] == token[0] and len(match.group(1)) >= len(token) and not match.group(2).strip():
                    break
                closing += 1
            if closing == len(lines):
                diagnostic("unclosed_fence_visibility", sourceLine=number)
                break
            emit(start, offsets[closing + 1], number, closing + 1, "fenced_snippet")
            index = closing + 1
            continue
        if "<!--" in line or "{/*" in line:
            # Drop whole touched lines, including multiple comments on a closing
            # line. A second opener must not leak its multiline body as prose.
            cursor = 0
            comment_line = number - 1
            while comment_line < len(lines):
                opener = re.search(r"<!--|\{/\*", lines[comment_line][cursor:])
                if opener is None:
                    break
                cursor += opener.end()
                terminator = "-->" if opener.group() == "<!--" else "*/}"
                while comment_line < len(lines):
                    end_comment = lines[comment_line].find(terminator, cursor)
                    if end_comment >= 0:
                        cursor = end_comment + len(terminator)
                        break
                    comment_line += 1
                    cursor = 0
                if comment_line == len(lines):
                    diagnostic("unclosed_comment_visibility", sourceLine=number)
            index = min(len(lines), comment_line + 1)
            continue
        admonition = re.fullmatch(r":::(note|tip|info|warning|danger|caution)(?:[ \t]+(.+))?", stripped)
        if admonition and not re.search(r"[{}<>]", admonition.group(2) or ""):
            wrappers.append((":::", len(result["sourceUnits"])))
            if admonition.group(2):
                label_start = start + line.index(admonition.group(2))
                emit(label_start, label_start + len(admonition.group(2)), number, number, "component_text")
            continue
        if stripped == ":::" and wrappers and wrappers[-1][0] == ":::":
            wrappers.pop()
            continue
        if stripped.startswith(":::"):
            diagnostic("uncertain_admonition_visibility", sourceLine=number)
            while index < len(lines) and lines[index].strip() != ":::":
                index += 1
            index = min(len(lines), index + 1)
            continue
        tag = re.search(r"<(/?)([A-Za-z][\w.]*)\b([^>]*)>", line)
        if tag:
            closing, name, props = tag.groups()
            safe = (name in STATIC_TAGS and not props.strip()) or (
                name == "Admonition" and (not props.strip() or re.fullmatch(r'''\s+type=["'](?:note|tip|info|warning|danger|caution)["']\s*''', props)))
            if safe:
                tail = line[tag.end():].strip()
                if closing and wrappers and wrappers[-1][0] == name and not tail:
                    wrappers.pop()
                    continue
                if not closing and not tail:
                    wrappers.append((name, len(result["sourceUnits"])))
                    continue
                inline = re.fullmatch(r"([^<>]+)</" + re.escape(name) + r">\s*", line[tag.end():])
                if not closing and inline and not re.search(r"[{}]", inline.group(1)):
                    emit(start + tag.end(), start + tag.end() + len(inline.group(1)), number, number, "component_text")
                    continue
            diagnostic("uncertain_component_visibility", sourceLine=number)
            if not closing and not props.rstrip().endswith("/"):
                # Unknown containers are opaque, including nested same-name tags.
                depth = 0
                cursor = number - 1
                token_re = re.compile(r"<(/?)" + re.escape(name) + r"\b[^>]*>")
                while cursor < len(lines):
                    for token_match in token_re.finditer(lines[cursor]):
                        if token_match.group(1):
                            depth -= 1
                        elif not token_match.group().endswith("/>"):
                            depth += 1
                    cursor += 1
                    if depth <= 0:
                        break
                index = cursor
            continue
        if "{" in line or "}" in line or re.match(r"^(import|export)\b", stripped):
            diagnostic("dynamic_or_runtime_content", sourceLine=number)
            index = _dynamic_end(lines, number - 1)
            continue
        if "<" in line or ">" in line or stripped.startswith((":::", "    ", "\t")) or line.startswith(("    ", "\t")):
            diagnostic("uncertain_markup_visibility", sourceLine=number)
            continue
        match = HEADING.match(line.rstrip("\r\n"))
        if match:
            heading = headings.get(number)
            heading_text = match.group(2).strip()
            kind = "heading"
        elif re.match(r"^\s*(?:[-+*]|\d+[.)])\s", line):
            kind = "list_text"
        elif "|" in line:
            kind = "table_text"
        else:
            kind = "prose"
        emit(start, end, number, number, kind)
    if wrappers:
        diagnostic("unclosed_static_wrapper_visibility")
        del result["sourceUnits"][wrappers[0][1]:]
    return result
