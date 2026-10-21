"""Deterministic technical packaging of accepted reader units; no new extraction rules."""
from __future__ import annotations

from copy import deepcopy
import importlib
from itertools import groupby
from pathlib import Path
from typing import Iterator

from src.extraction.llm import source_family_batch as adapter
from src.extraction.llm import source_family_inputs as sources

# Input overhead and output pressure are independently bounded. These are
# operational heuristics, not model limits or completeness/quality guarantees.
SIZING = dict(version='source-family-packaging/1.0', maxEnvelopeBytes=250000,
              maxSelectedTextBytes=24000, maxSelectedUnits=48, outputTokenCeiling=32768,
              rationale='At most 48 intact evidence units and 24KB selected text leave output room for '
                        'reasoning, independent node/edge evidence and structured records. '
                        '250KB bounds schema/instruction/catalog overhead independently. '
                        'These conservative heuristics cannot guarantee untruncated output.')


def fits(units: list) -> bool:
    """Bound output pressure without token counting or splitting evidence text."""
    return (len(units) <= SIZING['maxSelectedUnits'] and
            sum(len(u['text'].encode()) for u in units) <= SIZING['maxSelectedTextBytes'])


def blocks(owner: dict) -> list[list]:
    """Prefer coherent file/cell/section blocks; refine only oversized blocks."""
    units = owner['units']
    if fits(units):
        return [units] if units else []
    family = owner['family']
    def key(unit: dict) -> tuple:
        """Use only existing reader structure; never infer procedural semantics."""
        if family == 'github':
            return unit.get('path'), unit.get('cellIndex')
        if family == 'hydroshare':
            return unit.get('sourceField'), unit.get('source_path')
        headings = {h['ordinal']: h for h in owner['inputs']['page']['headings']}
        ordinal = unit.get('headingOrdinal')
        while ordinal in headings and headings[ordinal].get('parent_heading_ordinal') in headings:
            ordinal = headings[ordinal]['parent_heading_ordinal']
        return (ordinal,)
    result = []
    for _, rows in groupby(units, key=key):
        block = list(rows)
        if fits(block):
            result.append(block)
        else:
            for _, section in groupby(block, key=lambda u: (u.get('headingOrdinal'), u.get('headingContext'))):
                section = list(section)
                result.extend([section] if fits(section) else [[u] for u in section])
    return result


def ancestor_units(owner: dict, units: list) -> list:
    """Locate original ancestor prose using only the existing heading hierarchy."""
    if owner['family'] != 'ciroh_hub':
        return []
    headings = {h['ordinal']: h for h in owner['inputs']['page']['headings']}
    ancestors = set()
    for unit in units:
        ordinal = unit.get('headingOrdinal')
        while ordinal in headings:
            ordinal = headings[ordinal].get('parent_heading_ordinal')
            if ordinal is None:
                break
            ancestors.add(ordinal)
    return [u for u in owner['units']
            if u.get('headingOrdinal') in ancestors and u.get('contentKind') != 'fenced_snippet']


def context(owner: dict, units: list) -> list:
    """Repeat fitting original ancestor prose; explicitly report omissions at emission."""
    selected = {u['sourceUnitID'] for u in units}
    retained = list(units)
    for unit in reversed(ancestor_units(owner, units)):
        if unit['sourceUnitID'] not in selected and fits(retained + [unit]):
            retained.append(unit)
            selected.add(unit['sourceUnitID'])
    return [u for u in owner['units'] if u['sourceUnitID'] in selected]


def requests(owner: dict) -> Iterator[tuple[dict | None, dict]]:
    """Greedily pack intact coherent groups and explicitly retain every held unit."""
    contract = importlib.import_module('src.extraction.llm.' + adapter.conformance.DIRECTORIES[owner['family']] + '.request_contract')

    def attempt(units: list) -> tuple[dict | None, dict]:
        """Check the complete provider envelope without changing evidence units."""
        selected = context(owner, units)
        ids = [u['sourceUnitID'] for u in units]
        coverage = dict(ownerID=owner['ownerID'], family=owner['family'], primarySourceUnitIDs=ids,
                        sourceRecordSha256=owner['sourceRecordSha256'],
                        endpointRecordSha256=owner['endpointRecordSha256'])
        coverage['omittedAncestorContextUnitIDs'] = [u['sourceUnitID'] for u in ancestor_units(owner, units)
                                                    if u['sourceUnitID'] not in {s['sourceUnitID'] for s in selected}]
        reason = None
        if not fits(selected):
            reason = 'unit_or_required_ancestor_context_exceeds_operational_output_budget'
        else:
            inputs = {**owner['inputs'], 'selected_unit_ids': [u['sourceUnitID'] for u in selected]}
            request = contract.build_request(**inputs)
            if request['status'] != 'request_ready':
                reason = 'accepted_request_builder_failed'
                coverage['diagnostics'] = request['diagnostics']
            else:
                p = adapter.prepare(request, inputs)
                if len(adapter.canonical(p['body'])) > SIZING['maxEnvelopeBytes']:
                    reason = 'full_envelope_exceeds_operational_input_budget'
                else:
                    coverage.update(selectedSourceUnitIDs=inputs['selected_unit_ids'],
                                    repeatedContextUnitIDs=[u['sourceUnitID'] for u in selected if u['sourceUnitID'] not in ids])
                    return p, coverage
        return None, {**coverage, 'holdReason': reason}

    def emit(units: list) -> Iterator[tuple[dict | None, dict]]:
        """Use the largest verified contiguous prefix, never binary-halving output groups."""
        while units:
            whole = attempt(units)
            if whole[0] is not None or len(units) == 1:
                yield whole
                return
            # Find a manageable prefix; every unsuccessful singleton is retained
            # as an explicit hold while later independent units remain eligible.
            lo, hi, best = 1, len(units) - 1, None
            while lo <= hi:
                size = (lo + hi) // 2
                candidate = attempt(units[:size])
                if candidate[0] is not None:
                    best = size, candidate
                    lo = size + 1
                else:
                    hi = size - 1
            size, candidate = best if best is not None else (1, attempt(units[:1]))
            yield candidate
            units = units[size:]

    pending = []
    for block in blocks(owner):
        if pending and not fits(context(owner, pending + block)):
            yield from emit(pending)
            pending = []
        pending.extend(block)
    if pending:
        yield from emit(pending)


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
