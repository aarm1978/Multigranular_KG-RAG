"""Scope-preserving first-pass packing for the frozen collective adjudication inventory."""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from pathlib import Path
import yaml

from src.evaluation import step14_collective_adjudication as collective

w = collective.w
ROOT = collective.ROOT.parent / 'v2'
LIMIT = 12


def pack(scopes, limit=LIMIT):
    """Place whole scopes, preferring existing related windows with the least extra context."""
    groups = {tuple(sorted(s['occurrenceIDs'])) for s in scopes
              if s['status'] == 'prepared' and len(s['occurrenceIDs']) <= limit}
    degree = Counter(o for group in groups for o in group)
    windows = []
    postings = defaultdict(set)
    open_windows = defaultdict(set)
    # Large memberships first. Group hub neighborhoods together at equal size.
    def order(group):
        return -len(group), tuple(sorted((-degree[o], o) for o in group))

    for group in sorted(groups, key=order):
        members = set(group)
        w.require(2 <= len(members) == len(group), 'INVALID_SCOPE')
        if set.intersection(*(postings[o] for o in group)):
            continue
        feasible = (i for i in set.union(*(open_windows[o] for o in group))
                    if len(windows[i] | members) <= limit)
        index = min(feasible, key=lambda i: (len(members - windows[i]), -len(windows[i]), i),
                    default=len(windows))
        if index == len(windows):
            windows.append(set())
        for o in members - windows[index]:
            postings[o].add(index)
            open_windows[o].add(index)
        windows[index].update(members)
        if len(windows[index]) == limit:
            for o in windows[index]:
                open_windows[o].discard(index)
    return {f'P{i:05}': sorted(ids) for i, ids in enumerate(windows, 1)}


def index_units(units):
    """Index all appearances, including repeated occurrences across requests."""
    index = defaultdict(set)
    contexts = set()
    for uid, ids in units.items():
        key = frozenset(ids)
        w.require(len(ids) == len(key) <= LIMIT and key and key not in contexts, 'DUPLICATE_OR_INVALID_CONTEXT')
        contexts.add(key)
        for o in ids:
            index[o].add(uid)
    return index


def presentation(scope, index):
    """Measure input co-presence independently of model output or any identity decision."""
    if scope['status'] != 'prepared':
        return 'excluded', []
    members = scope['occurrenceIDs']
    joint = sorted(set.intersection(*(index[o] for o in members)))
    if joint:
        return 'fully_co_present', joint
    return ('split' if all(index[o] for o in members) else 'missing_members'), []


def audit(scopes, old, new):
    """Preserve exact original exclusions and flag oversized memberships independently."""
    old_index, new_index = index_units(old), index_units(new)
    rows = []
    for scope in scopes:
        before, old_ids = presentation(scope, old_index)
        after, new_ids = presentation(scope, new_index)
        ids = scope['occurrenceIDs']
        oversized = len(ids) > LIMIT
        if scope['status'] == 'prepared' and not oversized:
            w.require(new_ids, 'MISSING_JOINT_PRESENTATION:' + scope['candidateID'])
        rows.append(dict(scope, size=len(ids), overLimit=oversized, v1=before, v2=after,
                         v1JointRequests=old_ids, v2JointRequests=new_ids,
                         pendingBoundedReconciliation=oversized and scope['status'] == 'prepared'))
    return rows


def inputs(folder):
    """Resolve actual provider-visible entity aliases for each dispatchable request."""
    bindings = w.live.load(folder / 'alias-bindings.json')
    result = {}
    for request in w.r.rows(folder / 'requests.jsonl'):
        uid = request['custom_id']
        aliases = [e['occurrenceID'] for e in w.json.loads(request['body']['input'])['occurrences']]
        w.require(uid not in result and len(aliases) == len(set(aliases)) and
                  set(aliases) == bindings[uid].keys(), 'REQUEST_BINDING_DRIFT')
        result[uid] = [bindings[uid][a] for a in aliases]
    w.require(result.keys() == bindings.keys(), 'REQUEST_SET_DRIFT')
    return result


def all_inputs(root, packages):
    """Require shard and pilot request IDs to form one disjoint population."""
    result = {}
    for name in packages:
        batch = inputs(root / name)
        w.require(result.keys().isdisjoint(batch), 'DUPLICATE_DISPATCH_UNIT')
        result.update(batch)
    return result


def write_rows(path, rows):
    """Write immutable JSONL in stable order."""
    with path.open('xb') as stream:
        for row in rows:
            stream.write(w.live.encode(row) + b'\n')


def profile(rows):
    """Count exact size, lane, eligibility, exclusion reason and presentation together."""
    counts = Counter((r['lane'], r['size'], r['status'], r['v1'], r['v2']) for r in rows)
    return [dict(lane=l, size=n, overLimit=n > LIMIT, eligibility=s, v1=a, v2=b, count=count)
            for (l, n, s, a, b), count in sorted(counts.items())]


def prepare(root=ROOT, source=collective.ROOT):
    """Repack only the hash-verified v1 population and reuse its source evidence."""
    baseline = collective.verify(source)
    w.require(not root.exists(), 'FRESH_OUTPUT_REQUIRED')
    scopes = list(w.r.rows(source / 'coverage.jsonl'))
    old = all_inputs(source, baseline['packages'])
    units = pack(scopes)
    rows = audit(scopes, old, units)
    lanes = defaultdict(set)
    boundary = set()
    for row in rows:
        for uid in row['v2JointRequests']:
            lanes[uid].add(row['lane'])
            if row['v1'] == 'split':
                boundary.add(uid)
    provenance = {e['occurrenceID']: e for e in w.r.rows(source / 'occurrence-provenance.jsonl')}
    ends = {o: p['endpoint'] for o, p in provenance.items()}
    members = {o: p['member'] for o, p in provenance.items()}
    spec = yaml.safe_load(w.SPEC.read_text())
    template = next(w.r.rows(source / 'requests.jsonl'))['body']
    # Include previously split scopes in the overlap lane. Fill by new lane/family profiles.
    pilot = []
    profiles = set()
    for uid in sorted(units, key=lambda u: (u not in boundary, 'overlap' not in lanes[u], u)):
        families = frozenset(f for o in units[uid] for f in ends[o]['sourceFamilies'])
        key = (frozenset(lanes[uid]), families, uid in boundary)
        if key not in profiles:
            pilot.append(uid)
            profiles.add(key)
        if len(pilot) == 10:
            break
    pilot.extend([u for u in units if u not in pilot][:10-len(pilot)])
    w.require(len(pilot) == 10, 'PILOT_SIZE')
    rest = [u for u in units if u not in pilot]
    packages = {'pilot': pilot, 'batch-001': rest[:100]}
    for i in range(100, len(rest), 1000):
        packages[f'batch-{(i-100)//1000+2:03}'] = rest[i:i+1000]
    pins = {str(p): w.r.identity.sha(p) for p in
            (Path(__file__), Path(collective.__file__), w.SPEC, source / 'manifest.json')}
    root.mkdir(parents=True)
    sizes = {}
    for name, ids in packages.items():
        folder = root / name
        folder.mkdir()
        aliases, sources = {}, {}
        with (folder / 'requests.jsonl').open('xb') as out:
            for uid in ids:
                body, aliases[uid], sources[uid] = collective.make_body(units[uid], ends, members, spec, template)
                sizes[uid] = len(w.live.encode(body))
                out.write(w.live.encode(dict(custom_id=uid, method='POST', url='/v1/responses', body=body)) + b'\n')
        w.live.save(folder / 'alias-bindings.json', aliases)
        w.live.save(folder / 'source-artifact-bindings.json', sources)
        w.live.save(folder / 'summary.json', dict(requests=len(ids)))
        w.live.save(folder / 'manifest.json', dict(inputHashes=pins, outputHashes={
            p.name: w.r.identity.sha(p) for p in folder.iterdir()}))
    write_rows(root / 'coverage-audit.jsonl', rows)
    write_rows(root / 'units.jsonl', (dict(unitID=u, occurrenceIDs=ids, lanes=sorted(lanes[u]),
                                           coversV1Boundary=u in boundary) for u, ids in units.items()))
    total = sum(sizes.values())
    summary = dict(source=str(source), requests=len(units), packages={k:len(v) for k,v in packages.items()},
                   pilotUnits=pilot, byLaneAndScopeSize=profile(rows),
                   requestsByLane=dict(Counter(l for ls in lanes.values() for l in ls)),
                   approximateInputTokens=[total//5,total//3],
                   approximateOutputTokens=[len(units)*1000,len(units)*5000],
                   occurrencePresentations=sum(map(len,units.values())),
                   distinctOccurrences=len(index_units(units)), providerCalls=0)
    w.live.save(root / 'summary.json', summary)
    w.live.save(root / 'manifest.json', dict(inputHashes=pins, outputHashes={
        str(p.relative_to(root)): w.r.identity.sha(p) for p in root.rglob('*') if p.is_file()}))
    return verify(root)


def verify(root):
    """Gate every shard against actual request payloads and the frozen eligibility inventory."""
    parent = root.parent if (root / 'alias-bindings.json').exists() else root
    summary = collective.verify(parent)
    if root != parent:
        w.require(root.name in summary['packages'], 'UNKNOWN_SHARD')
    source = Path(summary['source'])
    pins = w.live.load(parent / 'manifest.json')['inputHashes']
    w.require(w.r.identity.sha(source / 'manifest.json') == pins[str(source / 'manifest.json')], 'BASELINE_DRIFT')
    baseline = collective.verify(source)
    rows = audit(w.r.rows(source / 'coverage.jsonl'), all_inputs(source, baseline['packages']),
                 all_inputs(parent, summary['packages']))
    w.require(rows == list(w.r.rows(parent / 'coverage-audit.jsonl')), 'AUDIT_DRIFT')
    return summary


def main():
    """Run the offline preflight before handing a pilot or shard to the existing transport."""
    from unittest.mock import patch
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=['prepare','verify','live','submit','status','retrieve'])
    parser.add_argument('--root', type=Path, default=ROOT)
    args = parser.parse_args()
    if args.mode == 'prepare':
        result = prepare(args.root)
    elif args.mode == 'verify':
        result = verify(args.root)
    else:
        w.require((args.root / 'alias-bindings.json').exists(), 'SELECT_EXECUTION_PACKAGE')
        w.require((args.root.name == 'pilot') == (args.mode == 'live'), 'WRONG_EXECUTION_PACKAGE')
        pending = [u for u in inputs(args.root) if not (args.root/'execution'/f'{u}.intent.json').exists()]
        with patch.object(w, 'verify', verify), patch.object(w, 'validate', collective.validate):
            result = w.operate(args.root, args.mode, pending if args.mode == 'live' else None)
    print(w.json.dumps({k:v for k,v in result.items() if k != 'byLaneAndScopeSize'}, indent=2))


if __name__ == '__main__':
    main()
