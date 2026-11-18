"""Versioned collective validation and stress pilot over immutable v2 request bodies."""
from __future__ import annotations

import argparse
from collections import Counter
from pathlib import Path
import re
from unittest.mock import patch

from jsonschema import ValidationError
from src.evaluation import step14_collective_coverage as coverage

legacy = coverage.collective
w = legacy.w
SOURCE = coverage.ROOT
ROOT = SOURCE.parent / 'v3'
VERSION = 'collective-validation/0.3.0'


def validate(value, body):
    """Validate original partition fields. Nullable broaderReferent is descriptive text only."""
    w.Draft202012Validator(body['text']['format']['schema']).validate(value)
    payload = w.json.loads(body['input'])
    ends = {e['occurrenceID']: e for e in payload['occurrences']}
    refs = {q['evidenceID']: o for o, e in ends.items() for q in e['evidence']}
    assigned = []
    for a in value['assessments']:
        ids = a['occurrenceIDs']
        assigned.extend(ids)
        w.require(ids and len(ids) == len(set(ids)), 'MEMBERSHIP')
        w.require(a['granularity'].strip() and a['rationale'].strip(), 'MISSING_REASONING')
        cited = a['supportingEvidenceIDs'] + a['contradictoryEvidenceIDs']
        w.require(all(q in refs and refs[q] in ids for q in cited), 'MISBOUND_EVIDENCE')
        if a['category'] != 'abstention':
            w.require({refs[q] for q in a['supportingEvidenceIDs']} == set(ids), 'UNCITED_MEMBER')
        if a['category'] == 'strict_identity':
            w.require(len(ids) >= 2 and len({ends[o]['ontologyClass'] for o in ids}) == 1, 'CLASS_OR_SIZE')
            w.require(not a['contradictoryEvidenceIDs'], 'CONTRADICTORY_IDENTITY')
            records = [dict(ends[o], labels=ends[o]['names'], versions=ends[o].get('versions', {}),
                            identifierDeclarations=[]) for o in ids]
            signals = legacy.ab.compatibility_signals(records, [])
            w.require(not signals['demonstratedConflicts'] and not signals['unresolvedAmbiguities'],
                      'INCOMPATIBLE_IDENTITY')
        else:
            w.require(len(ids) == 1, 'SINGLETON_ASSIGNMENT_REQUIRED')
    w.require(len(assigned) == len(set(assigned)) and set(assigned) == set(ends), 'EXACT_PARTITION_REQUIRED')
    # Delegate relations and gaps with neutral coverage witnesses, as in v2.
    witnesses = [dict(category='abstention', occurrenceIDs=[o], broaderReferent=None,
                      granularity='unassessed', supportingEvidenceIDs=[], contradictoryEvidenceIDs=[],
                      rationale='coverage witness', uncertainty='') for o in ends]
    legacy._relation_validate(dict(value, assessments=witnesses), body)


def process(root, uid, body, response):
    """Keep native responses and model text intact, including on validation failure."""
    folder = root / 'execution'
    w.live.save(folder / f'{uid}.response.json', response)
    report = dict(contract=VERSION, status='invalid_or_incomplete', identityApprovals=0,
                  semanticValidation=False, usage=response.get('usage'))
    try:
        w.require(response.get('status') == 'completed', 'INCOMPLETE_RESPONSE')
        value = w.transport.decode(w.live.provider.extract_model_output(response))
        validate(value, body)
        bindings = w.live.load(root / 'alias-bindings.json')[uid]
        resolved = w.resolve_output(value, bindings)
    except ValidationError as exc:
        report.update(errorType='ValidationError', failedRule='JSON_SCHEMA:' + str(exc.validator),
                      location=list(exc.absolute_path), detail=exc.message)
    except (ValueError, KeyError, TypeError, w.live.provider.OpenAIProviderError) as exc:
        report.update(errorType=type(exc).__name__, failedRule=str(exc))
    else:
        for suffix, data in [('hypotheses', value), ('resolved-hypotheses', resolved),
                             ('ontology-gaps', value['ontologyGaps'])]:
            w.live.save(folder / f'{uid}.{suffix}.json', data)
        report.update(status='validated_hypotheses_only', ontologyGapCount=len(value['ontologyGaps']))
    w.live.save(folder / f'{uid}.validation.json', report)
    return report


def features(request, unit):
    """Identify stress conditions from saved labels, quotes, classes and routing metadata."""
    payload = w.json.loads(request['body']['input'])
    ends = payload['occurrences']
    tags = set()
    n = len(ends)
    if n == 2:
        tags.add('pair')
    if 3 <= n <= 5:
        tags.add('small')
    if n >= 10 and 'overlap' in unit['lanes']:
        tags.add('large_overlap')
    if len({f for e in ends for f in e['sourceFamilies']}) > 1:
        tags.add('cross_family')
    if len({e['sourceArtifactRef'] for e in ends}) > 1:
        tags.add('cross_artifact')
    text = ' '.join(t for e in ends for t in [*e['names'], *(q['text'] for q in e['evidence'])])
    if re.search(r'\b(?:v\d+(?:\.\d+)*|version\s+\d|implementations?|releases?)\b', text, re.I):
        tags.add('version_or_implementation_cue')
    if 'typed_relation' in unit['lanes'] and any(
        a != b and x['ontologyClass'] in sig['compatibleSubjectClasses']
        and y['ontologyClass'] in sig['compatibleObjectClasses']
        for sig in payload['allowedPredicates'] for a,x in enumerate(ends) for b,y in enumerate(ends)
    ):
        tags.add('typed_lead_with_signature')
    if 'missing_information' in unit['lanes'] and any('granularity' not in e for e in ends):
        tags.add('abstention_challenge')
    return tags


def select(requests, units):
    """Use two fixed slots per challenge with cross-family variety as a tie breaker."""
    tags = {uid: features(r, units[uid]) for uid, r in requests.items()}
    selected = {}
    for role in ['pair','small','large_overlap','version_or_implementation_cue','typed_lead_with_signature',
                 'abstention_challenge','cross_family','pair','small','large_overlap']:
        eligible = [u for u in tags if role in tags[u] and u not in selected]
        w.require(eligible, 'UNAVAILABLE_STRESS_STRATUM:' + role)
        uid = min(eligible, key=lambda u: (sum(tags[u] == tags[s] for s in selected),
                                            'cross_family' not in tags[u], -len(tags[u]), u))
        selected[uid] = dict(role=role, tags=sorted(tags[uid]), occurrences=len(units[uid]['occurrenceIDs']))
    return selected


def verify(root):
    """Require v2 full coverage, immutable replay evidence and disjoint dispatch packages."""
    base = root if (root/'summary.json').exists() else root.parent
    summary = w.live.load(base/'summary.json')
    w.require(root == base or root.name in summary['packages'], 'UNKNOWN_DISPATCH_PACKAGE')
    manifest = w.live.load(base/'manifest.json')
    for path, digest in manifest['inputHashes'].items():
        w.require(w.r.identity.sha(Path(path)) == digest, 'INPUT_DRIFT:' + path)
    for name, digest in manifest['outputHashes'].items():
        w.require(w.r.identity.sha(base/name) == digest, 'OUTPUT_DRIFT:' + name)
    baseline = coverage.verify(SOURCE)
    original = coverage.all_inputs(SOURCE, baseline['packages'])
    tested = coverage.inputs(SOURCE/'pilot')
    future = coverage.all_inputs(base, summary['packages'])
    w.require(tested.keys().isdisjoint(future) and {**tested, **future} == original, 'COVERAGE_DRIFT')
    w.require(not list(SOURCE.glob('batch-*/execution/*.intent.json')), 'V2_BATCH_ALREADY_ATTEMPTED')
    return summary


def prepare(root=ROOT):
    """Revalidate original receipts once, then redistribute the remaining original requests."""
    baseline = coverage.verify(SOURCE)
    w.require(not root.exists() and not list(SOURCE.glob('batch-*/execution/*.intent.json')), 'FRESH_DISPATCH_REQUIRED')
    units = {r['unitID']:r for r in w.r.rows(SOURCE/'units.jsonl')}
    requests, aliases, sources, origins = {}, {}, {}, {}
    for name in baseline['packages']:
        folder = SOURCE/name
        aliases.update(w.live.load(folder/'alias-bindings.json'))
        sources.update(w.live.load(folder/'source-artifact-bindings.json'))
        for r in w.r.rows(folder/'requests.jsonl'):
            uid = r['custom_id']
            requests[uid] = r
            origins[uid] = name
    tested = baseline['pilotUnits']
    selected = select({u:r for u,r in requests.items() if u not in tested}, units)
    packages = {'stress-pilot':list(selected)}
    for name in sorted(set(origins.values()) - {'pilot'}):
        packages[name] = [u for u in requests if origins[u] == name and u not in selected]
    root.mkdir(parents=True)
    pins = {str(p):w.r.identity.sha(p) for p in (Path(__file__), SOURCE/'manifest.json')}
    replay = root/'revalidation'
    w.live.save(replay/'alias-bindings.json', {u:aliases[u] for u in tested})
    outcomes = {}
    for uid in tested:
        prefix = SOURCE/'pilot/execution'
        for suffix in ('intent','response','validation'):
            path = prefix/f'{uid}.{suffix}.json'
            pins[str(path)] = w.r.identity.sha(path)
        raw = w.live.load(prefix/f'{uid}.response.json')
        outcomes[uid] = process(replay, uid, requests[uid]['body'], raw)['status']
    for name, ids in packages.items():
        folder = root/name
        folder.mkdir()
        coverage.write_rows(folder/'requests.jsonl', (requests[u] for u in ids))
        w.live.save(folder/'alias-bindings.json', {u:aliases[u] for u in ids})
        w.live.save(folder/'source-artifact-bindings.json', {u:sources[u] for u in ids})
        w.live.save(folder/'manifest.json', dict(contract=VERSION, sourceManifest=pins[str(SOURCE/'manifest.json')],
                   outputHashes={p.name:w.r.identity.sha(p) for p in folder.iterdir()}))
    summary = dict(contract=VERSION, replay=outcomes, stress=selected,
                   packages={k:len(v) for k,v in packages.items()})
    w.live.save(root/'summary.json', summary)
    w.live.save(root/'manifest.json', dict(inputHashes=pins, outputHashes={
        str(p.relative_to(root)):w.r.identity.sha(p) for p in root.rglob('*') if p.is_file()}))
    return verify(root)


def main():
    """Use a single shared preflight and the existing immutable live/Batch transport."""
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('mode', choices=['prepare','verify','live','submit','status','retrieve'])
    p.add_argument('--root', type=Path, default=ROOT)
    a = p.parse_args()
    if a.mode == 'prepare':
        result = prepare(a.root)
    elif a.mode == 'verify':
        result = verify(a.root)
    else:
        w.require(a.root.name == 'stress-pilot' if a.mode == 'live' else a.root.name.startswith('batch-'),
                  'WRONG_EXECUTION_PACKAGE')
        with patch.object(w, 'verify', verify), patch.object(w, 'process', process):
            if a.mode == 'live':
                result = {}
                for uid in coverage.inputs(a.root):
                    if not (a.root/'execution'/f'{uid}.intent.json').exists():
                        result.update(w.operate(a.root, 'live', [uid]))
            else:
                result = w.operate(a.root, a.mode)
    print(w.json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
