"""Read-only structural triage of persisted GitHub/Hub verification and frozen text.

No reader, selector, extraction, semantic validator, MDX execution or provider is
invoked. Derived spans are diagnostic coordinates, never new eligible evidence.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import re
import socket
import subprocess
import tempfile
from unittest.mock import patch

from src.evaluation.source_family_production_verification import file_hash

ROOT = Path(__file__).resolve().parents[2]
REPORTS = Path('var/study2_step13/source-family-production-verification/v1')
OUTPUT = Path('var/study2_step13/semantic-coverage-diagnosis/v1')
CORPORA = {'github': 'data/interim/coderepos/ciroh_github_corpus.json',
           'ciroh_hub': 'data/interim/documents/ciroh_hub_corpus.json'}
LIMITS = ('Structural triage only, not scientific truth or eligibility attestation. '
          'Selected-but-uncited text is not a reader exclusion or proof of absence. '
          'Component declarations/props do not establish implementation or repository attribution. '
          'Procedure/Step evidence and Example/Parameter parent dependencies remain unchanged. '
          'Derived lexical spans are review targets, not restored source units. '
          'Counts describe records and deduplicated Unicode spans, not KG entities or accuracy.')
COORDS = ('startOffsetInAuthority', 'endOffsetInAuthority', 'startLine', 'endLine', 'sourceLine', 'cellIndex')


def require(value: bool, message: str) -> None:
    """Stop on inconsistent persisted identities, hashes or coordinates."""
    if not value:
        raise ValueError(message)


def sha(text: str) -> str:
    """Hash exact UTF-8 authority text, distinct from physical bytes."""
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


def rows(path: Path):
    """Read JSONL without opening any journal or modifying a report."""
    with path.open(encoding='utf-8') as handle:
        for number, line in enumerate(handle, 1):
            yield number, json.loads(line)


def merge(spans: list) -> list:
    """Deduplicate overlapping half-open spans within one authority/cell."""
    result = []
    for lo, hi in sorted(set(tuple(s) for s in spans)):
        if result and lo <= result[-1][1]:
            result[-1][1] = max(result[-1][1], hi)
        else:
            result.append([lo, hi])
    return result


def subtract(span: list | None, covered: list) -> list:
    """Measure unrepresented portions without declaring them semantically eligible."""
    if span is None:
        return []
    cursor, result = span[0], []
    for lo, hi in merge(covered):
        lo, hi = max(lo, span[0]), min(hi, span[1])
        if hi <= cursor or lo >= span[1]:
            continue
        if lo > cursor:
            result.append([cursor, lo])
        cursor = max(cursor, hi)
    if cursor < span[1]:
        result.append([cursor, span[1]])
    return result


def overlap(span: list | None, other: list | None) -> int:
    """Return intersecting Unicode characters, never infer coverage from labels."""
    return max(0, min(span[1], other[1]) - max(span[0], other[0])) if span and other else 0


def bounds(record: dict, text: str) -> list | None:
    """Use recorded offsets or explicitly derive a single original source line."""
    lo, hi = record.get('startOffsetInAuthority'), record.get('endOffsetInAuthority')
    if lo is not None or hi is not None:
        require(type(lo) is int and type(hi) is int and 0 <= lo < hi <= len(text), 'INVALID_STORED_OFFSETS')
        return [lo, hi]
    line = record.get('sourceLine')
    if line is not None:
        lines = text.splitlines(keepends=True)
        require(type(line) is int and 1 <= line <= len(lines), 'INVALID_STORED_LINE')
        lo = sum(map(len, lines[:line - 1]))
        return [lo, lo + len(lines[line - 1])]
    return None


def coordinates(text: str, span: list | None) -> dict | None:
    """Label diagnostic Unicode offsets and one-based original-authority lines."""
    if span is None:
        return None
    return dict(startOffsetInAuthority=span[0], endOffsetInAuthority=span[1],
                startLine=1 + len(re.findall(r'\r\n|\r|\n', text[:span[0]])),
                endLine=1 + len(re.findall(r'\r\n|\r|\n', text[:span[1] - 1])),
                coordinateStatus='derived_from_frozen_authority; not a reader/evidence span')


def mechanism(family: str, diagnostic: dict, literal: str) -> str:
    """Conservative causal labels from recorded reasons plus literal syntax only."""
    reason = diagnostic.get('reason', '')
    path = Path(diagnostic.get('path') or '').name.lower()
    if diagnostic.get('status') == 'failed_source_or_evidence_binding':
        return 'source_failure_or_unavailable_content'
    if reason in ('authority_recorded', 'phase_a_readme_authority', 'duplicate_manifest_path', 'notebook_json_read'):
        return 'authority_or_duplicate_bookkeeping'
    if family == 'github':
        if reason == 'content_kind_or_purpose_requires_review' and path.startswith(('changelog', 'contributing')):
            return 'trusted_passage_gate_' + ('changelog' if path.startswith('changelog') else 'contributing')
        if 'passage_review' in reason:
            return 'trusted_passage_review_unresolved'
        if reason in ('administrative_or_machine_file', 'license_legal_text_step11_4_2'):
            return 'administrative_or_legal_exclusion'
        if reason in ('non_prose_file_type', 'not_downloaded', 'unrecognized_selection_reason', 'extension_metadata_mismatch'):
            return 'file_selector_' + reason
        if re.search(r'pull requests?|code of conduct|copyright|all rights reserved|contributor license', literal, re.I):
            return 'administrative_passage_filter'
        if re.match(r'\s*(?:```|~~~|\$|import |from \S+ import |def |class |#!|[\w.-]+\s*[:=])', literal):
            return 'code_or_configuration_filter'
        if re.search(r'<[A-Za-z/!]|^\s*(?:>|\.\. |\{|!\[)', literal):
            return 'markup_filtered_prose_candidate' if len(re.findall(r'[A-Za-z]{3,}', re.sub(r'<[^>]*>', '', literal))) >= 3 else 'markup_or_media_filter'
        return 'unresolved_content_or_purpose'
    if re.search(r'<GitHub(?:Readme|WikiPage)\b[^>]*?/>', literal):
        return 'self_closing_external_component_marker'
    if reason == 'unclosed_static_wrapper_visibility':
        return 'unclosed_static_wrapper_unit_rollback'
    if reason == 'dynamic_or_runtime_content':
        return 'dynamic_expression_or_module_declaration'
    if reason == 'uncertain_admonition_visibility':
        return 'bracket_title_admonition' if re.search(r':::\w+\[', literal) else 'unresolved_admonition'
    if reason == 'uncertain_component_visibility':
        tags = re.findall(r'</?([A-Za-z][\w.]*)\b', literal)
        if tags and all(t.islower() for t in tags):
            return 'nested_or_attributed_static_html_candidate'
        return 'unresolved_component_visibility'
    if reason == 'uncertain_markup_visibility':
        return 'markup_filtered_static_text_candidate'
    return reason or 'unresolved_diagnostic'


def lexical_extent(text: str, span: list | None, label: str) -> tuple[list | None, str]:
    """Bound simple opaque wrappers for review without executing or selecting MDX."""
    if span is None:
        return None, 'no_measurable_boundary'
    literal = text[span[0]:span[1]]
    if label in ('bracket_title_admonition', 'unresolved_admonition'):
        close = re.search(r'^\s*:::\s*$', text[span[1]:], re.M)
        if close:
            return [span[0], span[1] + close.end()], 'derived_first_admonition_terminator; nested_boundary_unverified'
    if label == 'nested_or_attributed_static_html_candidate':
        tag = re.search(r'<([a-z][\w]*)\b[^>]*>', literal)
        if tag and not tag.group().endswith('/>'):
            depth = 0
            for token in re.finditer(r'</?' + re.escape(tag[1]) + r'\b[^>]*>', text[span[0]:]):
                depth += -1 if token.group().startswith('</') else (0 if token.group().endswith('/>') else 1)
                if depth == 0:
                    return [span[0], span[0] + token.end()], 'derived_balanced_same_tag_extent; static_candidate_only'
    return span, 'diagnostic_anchor_only; broader_effect_not_measured'


class Authorities:
    """Resolve only referenced frozen authorities; never invoke production readers."""

    def __init__(self, repo: Path, corpora: dict):
        """Index exact accepted owner identities from the two frozen snapshots."""
        self.repo, self.cache = repo, {}
        self.owners = {'github': {'github:repo:' + str(r['repo_id']): r for r in corpora['github']['repos']},
                       'ciroh_hub': {'hub:page:' + sha(p['canonical_url'])[:20]: p for p in corpora['ciroh_hub']['pages']}}
        self.raw_hashes = {}

    def get(self, family: str, owner: str, meta: dict) -> dict:
        """Hash exact decoded text; missing unpinned raw content stays unresolved."""
        require(owner in self.owners[family], 'UNKNOWN_SOURCE_OWNER:' + owner)
        source = self.owners[family][owner]
        path = source['page_key'] if family == 'ciroh_hub' else meta.get('path')
        cell = meta.get('cellIndex')
        key = family, owner, path, cell
        if key not in self.cache:
            text, raw_sha, state = None, None, 'authority_unavailable'
            if family == 'ciroh_hub':
                text = source['content_mdx']
                require(sha(text) == source['content_sha256'], 'HUB_CONTENT_HASH_DRIFT')
            elif path and (meta.get('authorityKind') == 'phase_a_readme' or
                           path == (source.get('readme') or {}).get('source_path')):
                text = source['readme'].get('text')
            elif path:
                relative = Path('data/raw/coderepos') / source['name'] / 'contents' / path
                physical = (self.repo / relative).resolve()
                base = (self.repo / 'data/raw/coderepos' / source['name'] / 'contents').resolve()
                require(not Path(path).is_absolute() and '..' not in Path(path).parts and physical.is_relative_to(base), 'UNSAFE_RAW_PATH')
                if physical.is_file():
                    raw = physical.read_bytes()
                    raw_sha = hashlib.sha256(raw).hexdigest()
                    self.raw_hashes[str(relative)] = raw_sha
                    try:
                        text = raw.decode('utf-8-sig')
                    except UnicodeDecodeError:
                        text = raw.decode('latin-1')
                    text = text.replace('\r\n', '\n').replace('\r', '\n').lstrip('\ufeff')
                    if cell is not None:
                        notebook = json.loads(raw.decode('utf-8-sig'))
                        require(type(cell) is int and 0 <= cell < len(notebook['cells']), 'INVALID_CELL_INDEX')
                        item = notebook['cells'][cell]
                        require(item['cell_type'] == 'markdown', 'NON_MARKDOWN_CELL')
                        text = item['source']
                        text = ''.join(text) if isinstance(text, list) else text
                elif meta.get('rawFileSha256'):
                    raise ValueError('PINNED_RAW_SOURCE_MISSING:' + str(relative))
            if text is not None:
                state = 'snapshot_authority' if family == 'ciroh_hub' or raw_sha is None else 'raw_decoded; acquisition_not_independently_verified'
            self.cache[key] = dict(key=list(key), path=path, cellIndex=cell, text=text,
                                   authorityTextSha256=sha(text) if text is not None else None,
                                   physicalBytesSha256=raw_sha, authorityStatus=state)
        result = self.cache[key]
        for field in ('authorityTextSha256', 'rawFileSha256'):
            expected = meta.get(field)
            actual = result['authorityTextSha256' if field == 'authorityTextSha256' else 'physicalBytesSha256']
            if expected is not None:
                require(actual == expected, 'SOURCE_HASH_DRIFT:' + field)
        if family == 'ciroh_hub' and meta.get('page_key'):
            require(meta['page_key'] == source['page_key'], 'PAGE_IDENTITY_DRIFT')
        if family == 'github':
            for field, expected in [('full_name', source['full_name']), ('frozenCommitSha', source['archive']['frozen_commit_sha'])]:
                require(meta.get(field, expected) == expected, 'REPOSITORY_IDENTITY_DRIFT')
        return result


def coverage(span: list | None, units: list) -> dict:
    """Intersect recorded selection/evidence only; retain distinct denominators."""
    selected, cited, reader = [], [], []
    references, ids = [], []
    for unit in units:
        s = unit['_span']
        if overlap(span, s):
            ids.append(unit['sourceUnitID'])
            reader.append([max(span[0], s[0]), min(span[1], s[1])])
            if unit['selected']:
                selected.append(reader[-1])
            for ref in unit['acceptedEvidenceReferences']:
                e = ref['evidence']
                es = [e['startOffsetInAuthority'], e['endOffsetInAuthority']]
                if overlap(span, es):
                    cited.append([max(span[0], es[0]), min(span[1], es[1])])
                    references.append(ref)
    return dict(unrepresentedInReaderSpans=subtract(span, reader),
                readerUnitIDs=sorted(set(ids)), readerCharacters=sum(b-a for a,b in merge(reader)),
                selectedCharacters=sum(b-a for a,b in merge(selected)),
                citedCharacters=sum(b-a for a,b in merge(cited)), acceptedEvidenceReferences=references)


def component_context(text: str, marker: list, units: list) -> dict:
    """Inspect page context, never attribute the suffix to a repository/component."""
    suffix = [marker[1], len(text)]
    c = coverage(suffix, units)
    visible = re.sub(r'<[^>]*>|^\s*(?:import|export)\b[^\n]*', '', text[marker[1]:], flags=re.M)
    demonstrable = len(re.findall(r'[A-Za-z]{3,}', visible)) >= 3
    if not demonstrable:
        state = '4_no_materialized_content_demonstrable'
    elif c['selectedCharacters'] and not c['citedCharacters']:
        state = '3_materialized_page_text_selected_but_uncited'
    elif c['selectedCharacters']:
        state = '1_materialized_page_text_present_and_selected'
    else:
        state = 'materialized_page_text_present_selection_not_demonstrated'
    return dict(pageContextState=state, componentBoundaryState='5_insufficient_component_boundary_evidence',
                attribution='page-level suffix context only; NOT assigned to referenced repository',
                contextCoordinates=coordinates(text, suffix), **c)


def diagnose(family: str, owner: str, diagnostic: dict, authority: dict, units: list) -> dict:
    """Reconcile a preserved source diagnostic with structural and coverage facts."""
    text = authority['text']
    span = bounds(diagnostic, text) if text is not None else None
    literal = text[span[0]:span[1]] if span else ''
    label = mechanism(family, diagnostic, literal)
    extent, basis = lexical_extent(text or '', span, label)
    c = coverage(extent, units)
    state = ('unmeasurable' if extent is None else 'selected_but_uncited' if c['selectedCharacters'] and not c['citedCharacters']
             else 'selected_and_cited' if c['selectedCharacters'] else 'reader_admitted_not_selected' if c['readerCharacters']
             else 'not_in_recorded_reader_units')
    result = dict(recordType='source_diagnostic', family=family, ownerID=owner,
        path=authority['path'], cellIndex=authority['cellIndex'], authorityTextSha256=authority['authorityTextSha256'],
        physicalBytesSha256=authority['physicalBytesSha256'], authorityStatus=authority['authorityStatus'],
        originalDiagnostic=deepcopy(diagnostic), originalCoordinates={k: diagnostic[k] for k in COORDS if k in diagnostic},
        derivedCoordinates=coordinates(text or '', extent), extentBasis=basis, mechanism=label,
        coverageState=state, **c, literalExample=(text[extent[0]:extent[1]][:800] if extent else None),
        exampleTruncated=bool(extent and extent[1]-extent[0] > 800),
        candidateCorrectionTarget=None)
    targets = {
        'bracket_title_admonition': 'Review bracket-title admonition boundary handling while retaining literal coordinates.',
        'unclosed_static_wrapper_unit_rollback': 'Inspect the unmatched wrapper and rollback scope; no recovered units are asserted.',
        'nested_or_attributed_static_html_candidate': 'Review static HTML nesting/attributes and text visibility without evaluating MDX.',
        'markup_filtered_static_text_candidate': 'Inspect literal technical text filtered by markup visibility rules.',
        'markup_filtered_prose_candidate': 'Inspect markup-filtered prose against frozen GitHub context gates.',
        'trusted_passage_gate_changelog': 'Researcher review of descriptive/version passages; no automatic trusted-passage attestation.',
        'trusted_passage_gate_contributing': 'Researcher review of scientific/operational passages; no automatic trusted-passage attestation.',
    }
    if label in targets:
        result['candidateCorrectionTarget'] = dict(review=targets[label], eligibilityAttested=False)
    if label == 'self_closing_external_component_marker':
        result['componentContext'] = component_context(text, span, units)
    return result


def review_sample(records: list, limit: int, difficult: bool = False) -> list:
    """Round-robin distinct family/mechanism buckets and owners for bounded review."""
    buckets = defaultdict(list)
    seen = set()
    for r in records:
        hard = ('unresolved' in r['mechanism'] or r.get('derivedCoordinates') is None or 'componentContext' in r)
        if difficult != hard or (not difficult and not r.get('literalExample')):
            continue
        key = (r['family'], r['ownerID'], r['path'], json.dumps(r.get('derivedCoordinates'), sort_keys=True))
        if key not in seen:
            buckets[(r['family'], r['mechanism'])].append(r)
            seen.add(key)
    for bucket in buckets.values():
        bucket.sort(key=lambda r: (r['ownerID'], r['path'] or '', json.dumps(r.get('derivedCoordinates'), sort_keys=True)))
        # First example from each owner before additional examples from that owner.
        owner_rank = Counter()
        ranked = []
        for r in bucket:
            ranked.append((owner_rank[r['ownerID']], r))
            owner_rank[r['ownerID']] += 1
        bucket[:] = [r for _, r in sorted(ranked, key=lambda x: x[0])]
    result = []
    while len(result) < limit and any(buckets.values()):
        for key in sorted(buckets):
            if buckets[key] and len(result) < limit:
                result.append(buckets[key].pop(0))
    return result


def reconciled_diagnostics(owner_path: Path, exception_path: Path) -> list:
    """Compare exact diagnostic multisets per owner, preserving sealed multiplicity."""
    expected, observed, owners = Counter(), Counter(), set()
    result = []

    def identity(family: str, owner: str, record: dict) -> tuple:
        """Use every original field; key order is not diagnostic identity."""
        return family, owner, json.dumps(record, sort_keys=True, ensure_ascii=False, allow_nan=False)

    for _, row in rows(owner_path):
        family, owner = row['family'], row['ownerID']
        if family not in CORPORA:
            continue
        require((family, owner) not in owners, 'DUPLICATE_SEALED_OWNER')
        owners.add((family, owner))
        sealed = row['sealedCoverage']
        require((sealed['family'], sealed['ownerID']) == (family, owner), 'SEALED_OWNER_IDENTITY_DRIFT')
        for record in sealed['diagnostics']:
            expected[identity(family, owner, record)] += 1
    for number, row in rows(exception_path):
        if row.get('family') not in CORPORA or row.get('recordType') != 'source_diagnostic':
            continue
        observed[identity(row['family'], row['ownerID'], row['record'])] += 1
        result.append((number, row))
    missing = sum((expected - observed).values())
    unexpected = sum(n for key, n in observed.items() if key not in expected)
    duplicated = sum(max(0, n - expected[key]) for key, n in observed.items() if key in expected)
    require(not (missing or unexpected or duplicated),
            f'SOURCE_DIAGNOSTIC_RECONCILIATION_FAILED: missing={missing}, unexpected={unexpected}, duplicated={duplicated}')
    return result


def affected_tables(records: list, limit: int = 10) -> dict:
    """Rank structural spans across causes without counting overlaps twice."""
    groups = {'owners': {}, 'documents': {}}
    for r in records:
        if r['recordType'] != 'source_diagnostic' or r['mechanism'] == 'authority_or_duplicate_bookkeeping':
            continue
        unknown = r.get('derivedCoordinates') is None or r.get('coverageMeasurementIncomplete', False)
        spans = [] if unknown else r.get('unrepresentedInReaderSpans', [])
        if not unknown and not spans:
            continue
        authority = (r['path'], r.get('cellIndex'), r.get('authorityTextSha256'))
        for kind, key in [('owners', (r['ownerID'],)), ('documents', (r['ownerID'], r['path']))]:
            group = groups[kind].setdefault(key, dict(ownerID=r['ownerID'], paths=set(), spans=defaultdict(list),
                                                     unmeasurableRecords=0, causes=[]))
            group['paths'].add(r['path'])
            group['spans'][authority].extend(spans)
            group['unmeasurableRecords'] += int(unknown)
            group['causes'].append(dict(mechanism=r['mechanism'], originalReason=r['originalDiagnostic'].get('reason'),
                path=r['path'], cellIndex=r.get('cellIndex'), authorityTextSha256=r.get('authorityTextSha256'),
                reportReference=r.get('reportReference'), unmeasurable=bool(unknown),
                measuredUnrepresentedSpans=merge(spans)))
    result = dict(limitPerTable=limit, interpretation='Structural triage, not scientific loss; unions are per owner/path/hash/cell across causes.')
    for kind, groups_by_key in groups.items():
        items = []
        for key, group in groups_by_key.items():
            items.append(dict(ownerID=group['ownerID'], paths=sorted(group['paths'], key=lambda p: p or ''),
                **({'path': key[1]} if kind == 'documents' else {}),
                deduplicatedUnrepresentedCharacters=sum(b-a for spans in group['spans'].values() for a,b in merge(spans)),
                unmeasurableRecords=group['unmeasurableRecords'],
                causes=sorted(group['causes'], key=lambda c: json.dumps(c, sort_keys=True))))
        tie = lambda item: (item['ownerID'], item.get('path') or '')
        measured = sorted((i for i in items if i['deduplicatedUnrepresentedCharacters']),
                          key=lambda i: (-i['deduplicatedUnrepresentedCharacters'], *tie(i)))
        unknown = sorted((i for i in items if i['unmeasurableRecords']),
                         key=lambda i: (-i['unmeasurableRecords'], *tie(i)))
        result[kind] = dict(measured=measured[:limit], unmeasurable=unknown[:limit],
                            totalMeasuredGroups=len(measured), totalUnmeasurableGroups=len(unknown))
    return result


def affected_markdown(tables: dict) -> list:
    """Render bounded tables while retaining exact identities and cause labels."""
    def cell(value) -> str:
        """Escape Markdown delimiters without changing stored JSON identities."""
        return str(value).replace('\\', '\\\\').replace('|', '\\|').replace('\n', '<br>')

    lines = ['', tables['interpretation'], '']
    for kind in ('owners', 'documents'):
        for view, title in [('measured', 'Measured unrepresented spans'), ('unmeasurable', 'Unmeasurable cases')]:
            data = tables[kind]
            total = data['totalMeasuredGroups' if view == 'measured' else 'totalUnmeasurableGroups']
            lines.extend([f'### {title}: {kind} (top {len(data[view])} of {total})', '',
                '| Owner | Paths/pages | Unrepresented characters | Unmeasurable records | Causes |', '|---|---|---:|---:|---|'])
            for item in data[view]:
                paths = '<br>'.join(cell(p) if p is not None else '(unresolved path)' for p in item['paths'])
                causes = '<br>'.join(cell(m) for m in sorted({c['mechanism'] for c in item['causes']}))
                lines.append(f"| {cell(item['ownerID'])} | {paths} | {item['deduplicatedUnrepresentedCharacters']} | {item['unmeasurableRecords']} | {causes} |")
            lines.append('')
    lines.append('Exact diagnostic file/line, original reason, path/page, hash/cell and measured spans are retained in summary.json affectedTables causes.')
    return lines


def summarize(records: list) -> dict:
    """Count diagnostic occurrences separately from unique owners/files and span unions."""
    mechanisms = {}
    for label in sorted({r['mechanism'] for r in records}):
        subset = [r for r in records if r['mechanism'] == label]
        spans, unrepresented = defaultdict(list), defaultdict(list)
        for r in subset:
            c = r.get('derivedCoordinates')
            key = (r['ownerID'], r['path'], r.get('cellIndex'), r.get('authorityTextSha256'))
            unrepresented[key].extend(r.get('unrepresentedInReaderSpans', []))
            if c:
                spans[(r['ownerID'], r['path'], r.get('cellIndex'), r.get('authorityTextSha256'))].append(
                    [c['startOffsetInAuthority'], c['endOffsetInAuthority']])
        mechanisms[label] = dict(records=len(subset), owners=len({r['ownerID'] for r in subset}),
            filesOrPages=len({(r['ownerID'], r['path']) for r in subset if r['path'] is not None}),
            measuredAuthorities=len(spans), unmeasurableRecords=sum(r.get('derivedCoordinates') is None for r in subset),
            deduplicatedDiagnosticCharacters=sum(b-a for ss in spans.values() for a,b in merge(ss)),
            deduplicatedUnrepresentedCharacters=sum(b-a for ss in unrepresented.values() for a,b in merge(ss)))
    return dict(componentContextStates=dict(Counter(r['componentContext']['pageContextState'] for r in records if 'componentContext' in r)),
                coverageStates=dict(Counter(r['coverageState'] for r in records if 'coverageState' in r)),
                records=len(records), sourceDiagnosticRecords=sum(r['recordType']=='source_diagnostic' for r in records),
                owners=len({r['ownerID'] for r in records}), mechanisms=mechanisms, affectedTables=affected_tables(records),
                spanDenominator='per mechanism, owner, authority hash and notebook cell; mechanisms may overlap; unrepresented is not eligibility or scientific absence')


def analyze(repo: Path, reports: Path) -> tuple[dict, dict]:
    """Join existing report rows to pinned sources; never open a queue or a bundle."""
    inputs = [reports / name for name in ('verification.json', 'source-unit-coverage.jsonl', 'exceptions.jsonl', 'family-owner.jsonl')]
    hashes = {str(p.relative_to(repo)): file_hash(p) for p in inputs}
    diagnostic_rows = reconciled_diagnostics(inputs[3], inputs[2])
    verification = json.loads(inputs[0].read_text())
    corpora = {}
    for family, path in CORPORA.items():
        physical = repo / path
        require(file_hash(physical) == verification['persistedSourcePins'][path], 'FROZEN_CORPUS_HASH_DRIFT:' + path)
        hashes[path] = file_hash(physical)
        corpora[family] = json.loads(physical.read_text())
    authorities = Authorities(repo, corpora)
    grouped, output, unit_ids = defaultdict(list), {f: [] for f in CORPORA}, set()
    missing_metadata = set()
    for number, unit in rows(inputs[1]):
        family, owner = unit['family'], unit['ownerID']
        if family not in CORPORA:
            continue
        identity = family, owner, unit['sourceUnitID']
        require(identity not in unit_ids, 'DUPLICATE_UNIT_ID')
        unit_ids.add(identity)
        meta = unit['sourceMetadata']
        if meta is None:
            missing_metadata.add(identity)
            require(not unit['selected'] and not unit['acceptedEvidenceReferences'], 'SELECTED_UNIT_MISSING_METADATA')
            output[family].append(dict(recordType='unit_coverage', family=family, ownerID=owner, path=None,
                mechanism='unselected_unit_metadata_unavailable', originalCoverage=unit))
            continue
        authority = authorities.get(family, owner, meta)
        text = authority['text']
        require(text is not None, 'SELECTED_AUTHORITY_UNAVAILABLE')
        span = bounds(meta, text)
        require(span is not None, 'UNIT_COORDINATES_MISSING')
        for ref in unit['acceptedEvidenceReferences']:
            require(unit['selected'] and ref['requestID'] in unit['selectedRequestIDs'], 'EVIDENCE_SELECTION_DRIFT')
            e = ref['evidence']
            require(e['sourceUnitID'] == unit['sourceUnitID'], 'EVIDENCE_UNIT_DRIFT')
            es = bounds(e, text)
            require(es is not None and span[0] <= es[0] < es[1] <= span[1] and
                    text[es[0]:es[1]] == e['evidenceText'], 'STORED_EVIDENCE_COORDINATE_DRIFT')
            require(e.get('authorityTextSha256', sha(text)) == sha(text), 'EVIDENCE_AUTHORITY_DRIFT')
        require(unit['citedByAcceptedEvidence'] == bool(unit['acceptedEvidenceReferences']), 'CITATION_ACCOUNTING_DRIFT')
        unit['_span'] = span
        grouped[tuple(authority['key'])].append(unit)
        label = ('selected_and_cited' if unit['acceptedEvidenceReferences'] else 'selected_but_uncited' if unit['selected']
                 else 'production_excluded' if unit['excluded'] else 'reader_admitted_not_selected')
        output[family].append(dict(recordType='unit_coverage', family=family, ownerID=owner, path=authority['path'],
            cellIndex=authority['cellIndex'], authorityTextSha256=authority['authorityTextSha256'],
            mechanism=label, sourceUnitID=unit['sourceUnitID'],
            originalCoordinates={k: meta[k] for k in COORDS if k in meta},
            selectedRequestIDs=unit['selectedRequestIDs'], acceptedEvidenceReferences=unit['acceptedEvidenceReferences'],
            processingIncomplete=unit['processingIncomplete'], reportReference=dict(file=inputs[1].name, line=number)))
    diagnostics = []
    for number, row in diagnostic_rows:
        family = row.get('family')
        if family not in CORPORA or row.get('recordType') != 'source_diagnostic':
            continue
        authority = authorities.get(family, row['ownerID'], row['record'])
        record = diagnose(family, row['ownerID'], row['record'], authority, grouped[tuple(authority['key'])])
        linked = set(row['record'].get('sourceUnitIDs', []))
        if row['record'].get('sourceUnitID'):
            linked.add(row['record']['sourceUnitID'])
        unknown = sorted(uid for uid in linked if (family, row['ownerID'], uid) in missing_metadata)
        if unknown:
            record.update(linkedReaderUnitsWithoutMetadata=unknown, coverageMeasurementIncomplete=True,
                          coverageState='reader_admitted_metadata_unavailable', unrepresentedInReaderSpans=[])
        record['reportReference'] = dict(file=inputs[2].name, line=number)
        output[family].append(record)
        diagnostics.append(record)
    # Role metadata alone never establishes a selector exclusion.
    for owner, source in sorted(authorities.owners['github'].items()):
        for item in source.get('files', {}).get('downloaded', []):
            if item.get('file_role') != 'other':
                continue
            matches = [u for key, units in grouped.items() if key[:3] == ('github', owner, item.get('path')) for u in units]
            output['github'].append(dict(recordType='file_role_inventory', family='github', ownerID=owner,
                path=item.get('path'), mechanism='file_role_other_not_a_selector_decision', originalFileMetadata=item,
                selectedUnitIDs=[u['sourceUnitID'] for u in matches if u['selected']],
                diagnosticReferences=[r['reportReference'] for r in diagnostics if r['family']=='github' and
                                      r['ownerID']==owner and r['path']==item.get('path')]))
    for record in diagnostics:
        if 'componentContext' not in record:
            continue
        page = authorities.owners['ciroh_hub'][record['ownerID']]
        record['externalContentDeclarations'] = page.get('external_content_sources', [])
        context = record['componentContext']
        span = context['contextCoordinates']
        suffix = [span['startOffsetInAuthority'], span['endOffsetInAuthority']]
        exclusions = [r for r in diagnostics if r['family']=='ciroh_hub' and r['ownerID']==record['ownerID'] and
                      r['mechanism'] in ('bracket_title_admonition', 'nested_or_attributed_static_html_candidate',
                                         'markup_filtered_static_text_candidate') and r['derivedCoordinates'] and
                      r['coverageState']=='not_in_recorded_reader_units' and overlap(suffix,
                      [r['derivedCoordinates']['startOffsetInAuthority'], r['derivedCoordinates']['endOffsetInAuthority']])]
        context['structuralExclusionReferences'] = [r['reportReference'] for r in exclusions]
        if exclusions and context['selectedCharacters']:
            context['pageContextState'] = '2_materialized_page_text_present_partly_reader_excluded'
        context['selectedButUncited'] = bool(context['selectedCharacters'] and not context['citedCharacters'])
    # Missing declaration diagnostics are surfaced, not silently treated as unavailable text.
    for owner, page in sorted(authorities.owners['ciroh_hub'].items()):
        if page.get('external_content_sources') and not any(r['ownerID']==owner and 'componentContext' in r for r in diagnostics):
            output['ciroh_hub'].append(dict(recordType='component_declaration_inventory', family='ciroh_hub',
                ownerID=owner, path=page['page_key'], mechanism='external_declaration_boundary_unresolved',
                externalContentDeclarations=page['external_content_sources'],
                componentBoundaryState='5_insufficient_component_boundary_evidence'))
    for path, expected in {**hashes, **authorities.raw_hashes}.items():
        require(file_hash(repo / path) == expected, 'INPUT_CHANGED_DURING_DIAGNOSIS:' + path)
    summary = dict(version='semantic-coverage-diagnosis/1.0', limitations=LIMITS,
        inputHashes=hashes, referencedPhysicalFileHashes=authorities.raw_hashes,
        implementationSha256=file_hash(Path(__file__)), families={f:summarize(rs) for f,rs in output.items()},
        reportIntegrity='input hashes recorded and stable during run; no journal re-verification',
        examples=review_sample(diagnostics, 36), difficultCases=review_sample(diagnostics, 12, True))
    return output, summary


def run(repo: Path, reports: Path, output: Path) -> None:
    """Atomically publish only a new ignored diagnostic directory; reject overwrite."""
    repo, reports, output = repo.resolve(), reports.resolve(), output.resolve()
    allowed = repo / OUTPUT
    require(output == allowed or allowed in output.parents, 'OUTPUT_OUTSIDE_DIAGNOSIS_V1')
    require(not output.exists(), 'OUTPUT_ALREADY_EXISTS')
    require(reports.is_relative_to(repo) and not reports.is_relative_to(output), 'INVALID_REPORT_INPUT_ROOT')
    require(subprocess.run(['git', 'check-ignore', '-q', str(output / 'summary.json')], cwd=repo).returncode == 0,
            'OUTPUT_MUST_BE_IGNORED')
    with patch.object(socket, 'socket', side_effect=RuntimeError('OFFLINE_ONLY')):
        records, summary = analyze(repo, reports)
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.diagnosis-', dir=output.parent) as temporary:
        folder = Path(temporary)
        for family, items in records.items():
            with (folder / (family + '.jsonl')).open('w', encoding='utf-8') as handle:
                for item in items:
                    # Literal snippets are bounded to the separate researcher review artifact.
                    item = {k:v for k,v in item.items() if k not in ('literalExample', 'exampleTruncated')}
                    handle.write(json.dumps(item, sort_keys=True, ensure_ascii=False) + '\n')
        review = {k:summary.pop(k) for k in ('examples', 'difficultCases')}
        (folder / 'review.json').write_text(json.dumps(review, indent=2, sort_keys=True, ensure_ascii=False) + '\n')
        (folder / 'summary.json').write_text(json.dumps(summary, indent=2, sort_keys=True) + '\n')
        lines = ['# GitHub / CIROH Hub structural coverage diagnosis', '', LIMITS, '']
        for family, stats in summary['families'].items():
            lines.extend([f'## {family}', '', '| Mechanism | Records | Owners | Files/pages | Anchor/extent characters | Unrepresented characters |',
                          '|---|---:|---:|---:|---:|---:|'])
            for label, count in stats['mechanisms'].items():
                lines.append(f"| {label} | {count['records']} | {count['owners']} | {count['filesOrPages']} | {count['deduplicatedDiagnosticCharacters']} | {count['deduplicatedUnrepresentedCharacters']} |")
            lines.extend(['', stats['spanDenominator'], ''])
            lines.extend(affected_markdown(stats['affectedTables']))
        lines.append('See review.json for at most 36 diverse literal examples and 12 difficult cases. Counts are structural triage only.')
        (folder / 'summary.md').write_text('\n'.join(lines) + '\n')
        require(not output.exists(), 'OUTPUT_ALREADY_EXISTS')
        folder.rename(output)


def main() -> None:
    """Expose an explicitly offline report-only CLI."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--reports', type=Path, default=REPORTS)
    parser.add_argument('--output', type=Path, default=OUTPUT)
    args = parser.parse_args()
    run(ROOT, args.reports, args.output)
    print(str(args.output / 'summary.md'))


if __name__ == '__main__':
    main()
