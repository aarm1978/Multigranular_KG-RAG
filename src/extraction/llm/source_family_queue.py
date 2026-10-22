"""Source-specific production context packaging, independent of Batch transport.

HydroShare resources combine abstract/README units. GitHub documents (including
all Markdown cells of a notebook) remain separate, with no inferred justification
for cross-document combinations. Hub pages retain all reader-admitted content,
including RESOURCES_PAGE_DOCUMENTATION and possible Example-context units.
Only oversized documents/pages are divided along existing structural boundaries.
"""
from __future__ import annotations

import importlib
from itertools import groupby
import re
from typing import Iterator

from src.extraction.llm import source_family_batch as adapter

# Safety checks apply AFTER selecting the scientific context, never by unit count.
# These are planning margins, not claims about measured tokens or provider limits.
# 96 KiB / 4 bytes per token leaves 24,576 planned output tokens plus 8,192 for
# reasoning within the unchanged 32,768 ceiling. Output density can differ;
# authentic truncation still follows the existing bounded technical retry path.
SIZING = dict(version='source-family-packaging/1.1', maxEnvelopeBytes=1000000,
              maxSelectedTextBytes=98304, outputTokenCeiling=32768,
              grouping={'hydroshare': 'resource_abstract_and_readmes',
                        'github': 'autonomous_document_including_notebook_markdown_cells',
                        'ciroh_hub': 'whole_page_all_admitted_static_content'},
              rationale='Select complete resources/documents/pages first, without a unit-count cap. '
                        'Only exceptional full envelopes above 1MB or selected text above 96KiB '
                        'trigger structural subdivision. The text check plans 24,576 output tokens '
                        'at four source bytes per output token plus 8,192 reasoning tokens; '
                        'it is a heuristic, not an output-completeness guarantee. '
                        'Never trim ancestor context to pass a size check.')


def fits(units: list) -> bool:
    """Apply only the exceptional output-pressure check to an entire context."""
    return sum(len(u['text'].encode()) for u in units) <= SIZING['maxSelectedTextBytes']


def blocks(owner: dict) -> list[list]:
    """Select resource/page contexts or separate autonomous GitHub documents."""
    units = owner['units']
    if owner['family'] != 'github':
        return [units] if units else []
    # The reader emits each authority and its notebook cells in source order.
    # Notebook cells are NOT separate production requests by default.
    result = [list(rows) for _, rows in groupby(units, key=lambda u: u['path'])]
    paths = [rows[0]['path'] for rows in result]
    adapter.require(len(paths) == len(set(paths)), 'NONCONTIGUOUS_DOCUMENT_SOURCE_ORDER')
    return result


def structural_paths(owner: dict, units: list) -> dict[str, tuple]:
    """Index existing heading/cell structure for exceptional splitting only."""
    if owner['family'] == 'ciroh_hub':
        headings = {h['ordinal']: h for h in owner['inputs']['page']['headings']}
        result = {}
        for unit in units:
            path, ordinal = [], unit.get('headingOrdinal')
            while ordinal in headings:
                adapter.require(ordinal not in path, 'CYCLIC_HEADING_STRUCTURE')
                path.insert(0, ordinal)
                ordinal = headings[ordinal].get('parent_heading_ordinal')
            result[unit['sourceUnitID']] = tuple(path)
        return result
    if owner['family'] != 'github':
        return {u['sourceUnitID']: () for u in units}
    result = {}
    reader = owner['inputs']['reader_result']
    for (path, cell), rows in groupby(units, key=lambda u: (u['path'], u.get('cellIndex'))):
        authority = next(a for a in reader['authorities'] if a['path'] == path and a.get('cellIndex') == cell)
        # Reuse original Markdown heading boundaries for grouping, not eligibility.
        # Non-Markdown prose without these boundaries remains an indivisible block.
        positions, stack, offset, fence, comment = [], [], 0, None, False
        for line in authority['text'].splitlines(keepends=True):
            marker = re.match(r"^\s{0,3}(`{3,}|~{3,})", line)
            title = re.match(r"^ {0,3}(#{1,6})\s+(.+?)\s*$", line)
            if fence is not None or marker:
                if fence is None:
                    fence = marker.group(1)
                elif marker and marker.group(1)[0] == fence[0] and len(marker.group(1)) >= len(fence):
                    fence = None
            elif comment or '<!--' in line or '{/*' in line:
                comment = not ('-->' in line or '*/}' in line)
            elif title:
                level = len(title.group(1))
                while stack and stack[-1][0] >= level:
                    stack.pop()
                stack.append((level, offset))
                positions.append((offset, tuple(p[1] for p in stack)))
            offset += len(line)
        for unit in rows:
            ancestors = next((p for at, p in reversed(positions) if at <= unit['startOffsetInAuthority']), ())
            result[unit['sourceUnitID']] = ((cell,) if cell is not None else ()) + ancestors
    return result


def ancestor_units(units: list, selected: list, paths: dict) -> list:
    """Retain complete admitted ancestor sections, including unchanged Example context."""
    selected_paths = [paths[u['sourceUnitID']] for u in selected]
    return [u for u in units if any(len(paths[u['sourceUnitID']]) < len(p)
            and p[:len(paths[u['sourceUnitID']])] == paths[u['sourceUnitID']] for p in selected_paths)]


def requests(owner: dict) -> Iterator[tuple[dict | None, dict]]:
    """Keep approved contexts whole; subdivide only a demonstrated size exception."""
    contract = importlib.import_module('src.extraction.llm.' + adapter.conformance.DIRECTORIES[owner['family']] + '.request_contract')
    for document in blocks(owner):
        paths = structural_paths(owner, document)
        context_id = adapter.digest(adapter.canonical(dict(family=owner['family'], ownerID=owner['ownerID'],
            sourceRecordSha256=owner['sourceRecordSha256'], units=[u['sourceUnitID'] for u in document])))

        def attempt(units: list, split_reason: str | None = None) -> tuple[dict | None, dict]:
            """Verify complete context and envelope, retaining every original unit."""
            ids = [u['sourceUnitID'] for u in units]
            selected_ids = set(ids) | {u['sourceUnitID'] for u in ancestor_units(document, units, paths)}
            selected = [u for u in document if u['sourceUnitID'] in selected_ids]
            coverage = dict(ownerID=owner['ownerID'], family=owner['family'], primarySourceUnitIDs=ids,
                sourceRecordSha256=owner['sourceRecordSha256'], endpointRecordSha256=owner['endpointRecordSha256'],
                productionContextID=context_id, contextStrategy=SIZING['grouping'][owner['family']],
                documentPath=document[0].get('path') if owner['family'] == 'github' else None,
                exceptionalSplit=split_reason is not None, splitReason=split_reason,
                omittedAncestorContextUnitIDs=[], selectedSourceUnitIDs=[u['sourceUnitID'] for u in selected],
                repeatedContextUnitIDs=[u['sourceUnitID'] for u in selected if u['sourceUnitID'] not in ids])
            if not fits(selected):
                return None, {**coverage, 'holdReason': 'complete_context_exceeds_output_safety_margin'}
            inputs = {**owner['inputs'], 'selected_unit_ids': coverage['selectedSourceUnitIDs']}
            request = contract.build_request(**inputs)
            if request['status'] != 'request_ready':
                return None, {**coverage, 'holdReason': 'accepted_request_builder_failed', 'diagnostics': request['diagnostics']}
            prepared = adapter.prepare(request, inputs)
            if len(adapter.canonical(prepared['body'])) > SIZING['maxEnvelopeBytes']:
                return None, {**coverage, 'holdReason': 'complete_envelope_exceeds_input_safety_margin'}
            return prepared, coverage

        def emit(units: list, depth: int = 0, split_reason: str | None = None) -> Iterator[tuple[dict | None, dict]]:
            """Split oversized heading trees at coherent siblings, never arbitrary unit counts."""
            whole = attempt(units, split_reason)
            if whole[0] is not None or whole[1]['holdReason'] == 'accepted_request_builder_failed':
                yield whole
                return
            reason = split_reason or whole[1]['holdReason']
            if owner['family'] == 'hydroshare':
                yield whole  # Resource-level contract: report an exceptional hold, never fragment it.
                return
            groups = [list(rows) for _, rows in groupby(units, key=lambda u: paths[u['sourceUnitID']][:depth + 1])]
            while len(groups) == 1 and depth < max((len(paths[u['sourceUnitID']]) for u in units), default=0):
                depth += 1
                groups = [list(rows) for _, rows in groupby(units, key=lambda u: paths[u['sourceUnitID']][:depth + 1])]
            if len(groups) == 1:
                yield None, {**whole[1], 'splitReason': reason,
                             'holdReason': 'indivisible_section_or_required_context_exceeds_safety_margin'}
                return
            # Combine adjacent coherent siblings only within this oversized document.
            pending = []
            for group in groups:
                if pending and attempt(pending + group, reason)[0] is None:
                    yield from emit(pending, depth + 1, reason)
                    pending = []
                pending.extend(group)
            if pending:
                yield from emit(pending, depth + 1, reason)

        yield from emit(document)

def costs(p: dict) -> dict:
    """Offline byte-based planning scenarios, explicitly not provider token counts."""
    size = len(adapter.canonical(p['body']))
    # Include schema and envelope overhead; no cache benefit or retries assumed.
    inputs = {k: size / divisor for k, divisor in (('low', 4), ('pooled', 3), ('high', 2), ('outputCeiling', 1))}
    outputs = dict(low=2048, pooled=8192, high=16384, outputCeiling=32768)
    return dict(inputTokenEstimates=inputs, outputTokenScenarios=outputs,
        costUSD={k: (v * 1.25 * (2 if v > 272000 else 1) +
                      outputs[k] * 5 * (1.5 if v > 272000 else 1)) / 1e6 for k, v in inputs.items()},
        basis='UTF-8 full-envelope bytes / 4,3,2,1; output scenarios include reasoning. '
              'Conservative cache-write input rates; no assumed cache savings/retries; not measured tokens.')
