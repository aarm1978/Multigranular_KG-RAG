"""Explicit post-hoc reviewer exclusions, isolated from historical validators."""
from contextlib import contextmanager
from copy import deepcopy
from unittest.mock import patch
from src.extraction.llm.pilot_preflight import canonical, digest

VERSION = 'source-local-reviewer-adjudication/0.1.0'


def require(condition, reason):
    """Fail closed on an unbound or inconsistent reviewer decision."""
    if not condition:
        raise ValueError(reason)


def pin(check, body):
    """Bind an adjudication to authentic candidates, typed endpoints and literal offsets."""
    units = {u['sourceUnitID']: u for u in body['sourceUnits']}
    evidence = []
    for span in check['boundEvidence']:
        unit = units[span['sourceUnitID']]
        lo, hi = span['startOffsetInAuthority'], span['endOffsetInAuthority']
        require(unit['text'][lo:hi] == span['evidenceText'], 'ADJUDICATION_QUOTE_DRIFT')
        evidence.append(dict(sourceUnitID=span['sourceUnitID'], startOffset=lo, endOffset=hi,
            quoteSha256=digest(span['evidenceText'].encode()), sourceTextSha256=digest(unit['text'].encode()),
            sourceUnitSha256=digest(canonical(unit))))
    return dict(candidateID=check['candidateID'], ownerID=body['owner']['endpointID'],
        candidateSha256=digest(canonical(check['originalCandidate'])),
        boundEvidenceSha256=digest(canonical(check['boundEvidence'])), evidence=evidence,
        resolvedSource=deepcopy(check['resolvedSource']), resolvedTarget=deepcopy(check['resolvedTarget']))


def apply(validation, body, entries):
    """Exclude reviewed edges and release only their exact duplicate flags, never gates.

    Native construction subsequently recomputes duplicate selection and dependency
    closure. Explicit parent references remain unchanged, including excluded parents.
    """
    result = deepcopy(validation)
    checks = {c['candidateID']: c for c in result['candidateChecks']}
    excluded = {e['excluded']['candidateID'] for e in entries}
    require(len(excluded) == len(entries), 'DUPLICATE_ADJUDICATION')
    for entry in entries:
        for name in ('excluded', 'counterpart'):
            expected = entry[name]
            c = checks.get(expected['candidateID'])
            require(c is not None and c['kind'] == 'edge' and pin(c, body) == expected,
                    'ADJUDICATION_PIN_DRIFT')
        winner, counterpart = (checks[entry[k]['candidateID']] for k in ('excluded', 'counterpart'))
        require(counterpart.get('duplicateOf') == [winner['candidateID']], 'DUPLICATE_ASSOCIATION_DRIFT')
        require(winner['originalCandidate']['inventoryId'] == counterpart['originalCandidate']['inventoryId']
                and winner['resolvedSource'] == counterpart['resolvedSource']
                and winner['resolvedTarget'] == counterpart['resolvedTarget'], 'DUPLICATE_TRIPLE_DRIFT')
    for c in checks.values():
        references = set(c.get('duplicateOf', []))
        if references & excluded:
            require(c['kind'] == 'edge' and references <= excluded, 'AMBIGUOUS_DUPLICATE_RELEASE')
            c.pop('duplicateOf')
            c['suppressedDuplicate'] = False
            if c['disposition'] == 'suppressed_duplicate':
                c['disposition'] = c['validationDisposition']
        if c['candidateID'] in excluded:
            entry = next(e for e in entries if e['excluded']['candidateID'] == c['candidateID'])
            finding = dict(reason='reviewer_adjudicated_evidence_endpoint_mismatch',
                disposition='rejected_invalid_assertion', adjudicationID=entry['adjudicationID'],
                authority=VERSION, explanation=entry['reason'])
            c['findings'].append(finding)
            c['disposition'] = 'rejected_invalid_assertion'
            c['reviewerAdjudication'] = deepcopy(entry)
            result['diagnostics'].append(dict(candidateID=c['candidateID'], **finding))
    return result


@contextmanager
def overlay(entries):
    """Apply an explicitly scoped reviewer decision after enrichment, before construction."""
    from src.extraction.llm import source_local_semantics as local
    original = local.enrich_checks

    def enrich(prepared, payload, validation):
        """Retain native checks and authentic payload, then apply pinned exclusions."""
        original(prepared, payload, validation)
        revised = apply(validation, prepared['semanticRequest']['request'], entries)
        validation.clear()
        validation.update(revised)

    with patch.object(local, 'enrich_checks', enrich):
        yield
